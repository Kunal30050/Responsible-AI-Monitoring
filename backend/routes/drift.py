from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone, timedelta
import pandas as pd
import numpy as np

from database import get_db, PredictionLog, DriftMetric
from models.schemas import DriftAnalysisRequest, DriftMetricResponse
from drift_detection.engine import drift_engine
from alerting.engine import alerting_engine

router = APIRouter(prefix="/api/v1/drift", tags=["Drift Detection"])


@router.post("/analyze", response_model=list[DriftMetricResponse])
async def analyze_drift(payload: DriftAnalysisRequest, db: AsyncSession = Depends(get_db)):
    """Run drift detection comparing reference and current windows."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    ref_start = now - timedelta(hours=payload.reference_window_hours)
    cur_start = now - timedelta(hours=payload.current_window_hours)

    # Fetch reference data
    ref_result = await db.execute(
        select(PredictionLog)
        .where(
            PredictionLog.model_id == payload.model_id,
            PredictionLog.timestamp >= ref_start,
            PredictionLog.timestamp < cur_start,
        )
    )
    ref_logs = ref_result.scalars().all()

    # Fetch current data
    cur_result = await db.execute(
        select(PredictionLog)
        .where(
            PredictionLog.model_id == payload.model_id,
            PredictionLog.timestamp >= cur_start,
        )
    )
    cur_logs = cur_result.scalars().all()

    if len(ref_logs) < 30 or len(cur_logs) < 30:
        raise HTTPException(status_code=400, detail="Insufficient data for drift analysis (min 30 records per window)")

    # Convert to DataFrames
    def logs_to_df(logs):
        rows = []
        for l in logs:
            row = {**l.features, "prediction": l.prediction}
            rows.append(row)
        return pd.DataFrame(rows)

    ref_df = logs_to_df(ref_logs)
    cur_df = logs_to_df(cur_logs)

    # Detect data drift
    drift_results = drift_engine.detect_drift(ref_df, cur_df, features=payload.features)

    # Detect prediction drift
    pred_drift = drift_engine.detect_prediction_drift(
        ref_df["prediction"].values,
        cur_df["prediction"].values,
    )
    drift_results.extend(pred_drift)

    # Store results
    responses = []
    for dr in drift_results:
        drift_record = DriftMetric(
            model_id=payload.model_id,
            timestamp=now,
            drift_type=dr.drift_type,
            feature_name=dr.feature_name,
            statistic_name=dr.statistic_name,
            statistic_value=dr.statistic_value,
            p_value=dr.p_value,
            is_drifted=dr.is_drifted,
            details=dr.details,
        )
        db.add(drift_record)

        responses.append(DriftMetricResponse(
            feature_name=dr.feature_name,
            drift_type=dr.drift_type,
            statistic_name=dr.statistic_name,
            statistic_value=dr.statistic_value,
            p_value=dr.p_value,
            is_drifted=dr.is_drifted,
            timestamp=now,
        ))

        if dr.is_drifted:
            await alerting_engine.evaluate_and_alert(
                model_id=payload.model_id,
                metric_type="drift",
                metric_value=dr.statistic_value,
                metric_details={"feature": dr.feature_name, "test": dr.statistic_name},
            )

    await db.commit()
    return responses


@router.get("/{model_id}/history", response_model=list[DriftMetricResponse])
async def get_drift_history(model_id: int, hours: int = 168, db: AsyncSession = Depends(get_db)):
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=hours)
    result = await db.execute(
        select(DriftMetric)
        .where(DriftMetric.model_id == model_id, DriftMetric.timestamp >= cutoff)
        .order_by(DriftMetric.timestamp.desc())
    )
    records = result.scalars().all()
    return [
        DriftMetricResponse(
            feature_name=r.feature_name,
            drift_type=r.drift_type,
            statistic_name=r.statistic_name,
            statistic_value=r.statistic_value,
            p_value=r.p_value,
            is_drifted=r.is_drifted,
            timestamp=r.timestamp,
        )
        for r in records
    ]