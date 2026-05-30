from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone, timedelta

from database import get_db, BiasMetric, DriftMetric, RiskScore
from models.schemas import RiskScoreResponse
from risk_scoring.engine import risk_engine
from alerting.engine import alerting_engine

router = APIRouter(prefix="/api/v1/risk", tags=["Risk Scoring"])


@router.post("/{model_id}/compute", response_model=RiskScoreResponse)
async def compute_risk_score(model_id: int, hours: int = 24, db: AsyncSession = Depends(get_db)):
    """Compute composite risk score for a model."""
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=hours)

    # Fetch recent bias metrics
    bias_result = await db.execute(
        select(BiasMetric).where(BiasMetric.model_id == model_id, BiasMetric.timestamp >= cutoff)
    )
    bias_records = bias_result.scalars().all()
    bias_metrics = [
        {"metric_name": r.metric_name, "metric_value": r.metric_value, "is_fair": r.is_fair}
        for r in bias_records
    ]

    # Fetch recent drift metrics
    drift_result = await db.execute(
        select(DriftMetric).where(DriftMetric.model_id == model_id, DriftMetric.timestamp >= cutoff)
    )
    drift_records = drift_result.scalars().all()
    drift_metrics = [
        {"statistic_name": r.statistic_name, "statistic_value": r.statistic_value, "p_value": r.p_value, "is_drifted": r.is_drifted}
        for r in drift_records
    ]

    # Compute risk
    assessment = risk_engine.compute_risk(
        bias_metrics=bias_metrics,
        drift_metrics=drift_metrics,
    )

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # Store risk score
    record = RiskScore(
        model_id=model_id,
        timestamp=now,
        overall_score=assessment.overall_score,
        bias_score=assessment.bias_score,
        drift_score=assessment.drift_score,
        performance_score=assessment.performance_score,
        explainability_score=assessment.explainability_score,
        risk_level=assessment.risk_level,
        details=assessment.details,
    )
    db.add(record)
    await db.commit()

    # Alert if high risk
    if assessment.overall_score > 0.7:
        await alerting_engine.evaluate_and_alert(
            model_id=model_id,
            metric_type="risk",
            metric_value=assessment.overall_score,
            metric_details={"risk_level": assessment.risk_level},
        )

    return RiskScoreResponse(
        model_id=model_id,
        overall_score=assessment.overall_score,
        bias_score=assessment.bias_score,
        drift_score=assessment.drift_score,
        performance_score=assessment.performance_score,
        explainability_score=assessment.explainability_score,
        risk_level=assessment.risk_level,
        timestamp=now,
        details=assessment.details,
    )


@router.get("/{model_id}/history", response_model=list[RiskScoreResponse])
async def get_risk_history(model_id: int, hours: int = 168, db: AsyncSession = Depends(get_db)):
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=hours)
    result = await db.execute(
        select(RiskScore)
        .where(RiskScore.model_id == model_id, RiskScore.timestamp >= cutoff)
        .order_by(RiskScore.timestamp.desc())
    )
    records = result.scalars().all()
    return [
        RiskScoreResponse(
            model_id=r.model_id,
            overall_score=r.overall_score,
            bias_score=r.bias_score,
            drift_score=r.drift_score,
            performance_score=r.performance_score,
            explainability_score=r.explainability_score,
            risk_level=r.risk_level,
            timestamp=r.timestamp,
            details=r.details or {},
        )
        for r in records
    ]