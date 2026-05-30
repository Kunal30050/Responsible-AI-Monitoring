from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from datetime import datetime, timezone, timedelta

from database import get_db, MonitoredModel, PredictionLog, BiasMetric, DriftMetric, RiskScore, AlertHistory
from models.schemas import ModelRegistration, ModelResponse, PredictionInput, BatchPredictionInput, DashboardSummary
from kafka_layer.producer import send_prediction

router = APIRouter(prefix="/api/v1/models", tags=["Model Monitoring"])


@router.post("/register", response_model=ModelResponse)
async def register_model(payload: ModelRegistration, db: AsyncSession = Depends(get_db)):
    """Register a new model for monitoring."""
    model = MonitoredModel(
        name=payload.name,
        model_type=payload.model_type.value,
        description=payload.description,
        metadata_=payload.metadata or {},
    )
    db.add(model)
    await db.commit()
    await db.refresh(model)
    return model


@router.get("/", response_model=list[ModelResponse])
async def list_models(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MonitoredModel).where(MonitoredModel.is_active == True))
    return result.scalars().all()


@router.get("/{model_id}", response_model=ModelResponse)
async def get_model(model_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MonitoredModel).where(MonitoredModel.id == model_id))
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return model


@router.post("/predictions")
async def log_prediction(payload: PredictionInput):
    """Log a single prediction via Kafka."""
    await send_prediction(payload.model_dump())
    return {"status": "queued", "model_id": payload.model_id}


@router.post("/predictions/batch")
async def log_predictions_batch(payload: BatchPredictionInput):
    """Log batch predictions via Kafka."""
    for pred in payload.predictions:
        await send_prediction(pred.model_dump())
    return {"status": "queued", "count": len(payload.predictions)}


@router.get("/dashboard/summary", response_model=DashboardSummary)
async def get_dashboard_summary(db: AsyncSession = Depends(get_db)):
    """Get high-level dashboard metrics."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    yesterday = now - timedelta(hours=24)

    # Total models
    model_count = await db.execute(
        select(func.count()).select_from(MonitoredModel).where(MonitoredModel.is_active == True)
    )
    total_models = model_count.scalar() or 0

    # Predictions in last 24h
    pred_count = await db.execute(
        select(func.count()).select_from(PredictionLog).where(PredictionLog.timestamp >= yesterday)
    )
    total_predictions_24h = pred_count.scalar() or 0

    # Active (unacknowledged) alerts
    alert_count = await db.execute(
        select(func.count()).select_from(AlertHistory).where(AlertHistory.acknowledged == False)
    )
    active_alerts = alert_count.scalar() or 0

    # Avg risk score (latest per model)
    risk_result = await db.execute(
        select(func.avg(RiskScore.overall_score))
        .where(RiskScore.timestamp >= yesterday)
    )
    avg_risk = risk_result.scalar() or 0.0

    # Bias issues in last 24h
    bias_count = await db.execute(
        select(func.count()).select_from(BiasMetric)
        .where(BiasMetric.timestamp >= yesterday, BiasMetric.is_fair == False)
    )
    bias_issues = bias_count.scalar() or 0

    # Drift detected
    drift_count = await db.execute(
        select(func.count()).select_from(DriftMetric)
        .where(DriftMetric.timestamp >= yesterday, DriftMetric.is_drifted == True)
    )
    drift_detected = drift_count.scalar() or 0

    # Per-model summary
    models_result = await db.execute(select(MonitoredModel).where(MonitoredModel.is_active == True))
    models = models_result.scalars().all()

    model_summaries = []
    for m in models:
        latest_risk = await db.execute(
            select(RiskScore)
            .where(RiskScore.model_id == m.id)
            .order_by(RiskScore.timestamp.desc())
            .limit(1)
        )
        risk = latest_risk.scalar_one_or_none()

        model_summaries.append({
            "id": m.id,
            "name": m.name,
            "model_type": m.model_type,
            "risk_score": risk.overall_score if risk else None,
            "risk_level": risk.risk_level if risk else "unknown",
        })

    return DashboardSummary(
        total_models=total_models,
        total_predictions_24h=total_predictions_24h,
        active_alerts=active_alerts,
        avg_risk_score=round(float(avg_risk), 4),
        bias_issues=bias_issues,
        drift_detected=drift_detected,
        models=model_summaries,
    )