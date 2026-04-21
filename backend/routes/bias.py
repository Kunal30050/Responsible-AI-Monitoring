from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone, timedelta
import numpy as np

from database import get_db, PredictionLog, BiasMetric
from models.schemas import BiasAnalysisRequest, BiasMetricResponse
from bias_fairness.engine import BiasFairnessEngine
from alerting.engine import alerting_engine

router = APIRouter(prefix="/api/v1/bias", tags=["Bias & Fairness"])


@router.post("/analyze", response_model=list[BiasMetricResponse])
async def analyze_bias(payload: BiasAnalysisRequest, db: AsyncSession = Depends(get_db)):
    """Run bias analysis on recent predictions for a model."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=payload.lookback_hours)

    result = await db.execute(
        select(PredictionLog)
        .where(
            PredictionLog.model_id == payload.model_id,
            PredictionLog.timestamp >= cutoff,
            PredictionLog.actual.isnot(None),
        )
        .order_by(PredictionLog.timestamp.desc())
    )
    logs = result.scalars().all()

    if len(logs) < 20:
        raise HTTPException(status_code=400, detail="Not enough data for bias analysis (min 20 labeled records)")

    # Extract arrays
    y_true = np.array([l.actual for l in logs])
    y_pred = np.array([int(l.prediction >= 0.5) for l in logs])
    sensitive = np.array([
        l.protected_attributes.get(payload.protected_attribute, None)
        for l in logs
    ])

    # Filter out None values
    valid_mask = sensitive != None  # noqa
    y_true = y_true[valid_mask].astype(int)
    y_pred = y_pred[valid_mask].astype(int)
    sensitive = sensitive[valid_mask]

    if len(y_true) < 10:
        raise HTTPException(status_code=400, detail="Not enough records with the specified protected attribute")

    # Compute metrics
    engine = BiasFairnessEngine()
    metrics = engine.compute_all_metrics(
        y_true, y_pred, sensitive,
        payload.privileged_value, payload.unprivileged_value
    )

    # Store results and check alerts
    responses = []
    now = datetime.now(timezone.utc)
    for m in metrics:
        bias_record = BiasMetric(
            model_id=payload.model_id,
            timestamp=now,
            metric_name=m["metric_name"],
            protected_attribute=payload.protected_attribute,
            privileged_value=str(payload.privileged_value),
            unprivileged_value=str(payload.unprivileged_value),
            metric_value=m["metric_value"],
            is_fair=m["is_fair"],
            details=m.get("details", {}),
        )
        db.add(bias_record)

        responses.append(BiasMetricResponse(
            metric_name=m["metric_name"],
            protected_attribute=payload.protected_attribute,
            metric_value=m["metric_value"],
            is_fair=m["is_fair"],
            timestamp=now,
            details=m.get("details", {}),
        ))

        # Trigger alerts if unfair
        if not m["is_fair"]:
            await alerting_engine.evaluate_and_alert(
                model_id=payload.model_id,
                metric_type="bias",
                metric_value=m["metric_value"],
                metric_details={"metric_name": m["metric_name"], "protected_attribute": payload.protected_attribute},
            )

    await db.commit()
    return responses


@router.get("/{model_id}/history", response_model=list[BiasMetricResponse])
async def get_bias_history(model_id: int, hours: int = 168, db: AsyncSession = Depends(get_db)):
    """Get historical bias metrics for a model."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    result = await db.execute(
        select(BiasMetric)
        .where(BiasMetric.model_id == model_id, BiasMetric.timestamp >= cutoff)
        .order_by(BiasMetric.timestamp.desc())
    )
    records = result.scalars().all()
    return [
        BiasMetricResponse(
            metric_name=r.metric_name,
            protected_attribute=r.protected_attribute,
            metric_value=r.metric_value,
            is_fair=r.is_fair,
            timestamp=r.timestamp,
            details=r.details or {},
        )
        for r in records
    ]