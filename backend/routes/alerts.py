from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime, timezone, timedelta

from database import get_db, AlertRule, AlertHistory, AlertSeverity
from models.schemas import AlertRuleCreate, AlertHistoryResponse

router = APIRouter(prefix="/api/v1/alerts", tags=["Alerting"])


@router.post("/rules")
async def create_alert_rule(payload: AlertRuleCreate, db: AsyncSession = Depends(get_db)):
    """Create a new alert rule."""
    rule = AlertRule(
        name=payload.name,
        model_id=payload.model_id,
        metric_type=payload.metric_type,
        condition=payload.condition,
        threshold=payload.threshold,
        severity=AlertSeverity(payload.severity.value),
        channels=payload.channels,
        cooldown_minutes=payload.cooldown_minutes,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return {"id": rule.id, "name": rule.name, "status": "created"}


@router.get("/rules")
async def list_alert_rules(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AlertRule).where(AlertRule.is_active == True))
    rules = result.scalars().all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "model_id": r.model_id,
            "metric_type": r.metric_type,
            "condition": r.condition,
            "threshold": r.threshold,
            "severity": r.severity.value,
            "channels": r.channels,
            "is_active": r.is_active,
        }
        for r in rules
    ]


@router.delete("/rules/{rule_id}")
async def deactivate_rule(rule_id: int, db: AsyncSession = Depends(get_db)):
    await db.execute(
        update(AlertRule).where(AlertRule.id == rule_id).values(is_active=False)
    )
    await db.commit()
    return {"status": "deactivated"}


@router.get("/history", response_model=list[AlertHistoryResponse])
async def get_alert_history(
    model_id: int = None, hours: int = 168, limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    query = select(AlertHistory).where(AlertHistory.timestamp >= cutoff)
    if model_id:
        query = query.where(AlertHistory.model_id == model_id)
    query = query.order_by(AlertHistory.timestamp.desc()).limit(limit)

    result = await db.execute(query)
    records = result.scalars().all()
    return [
        AlertHistoryResponse(
            id=r.id,
            rule_id=r.rule_id,
            model_id=r.model_id,
            severity=r.severity.value,
            message=r.message,
            metric_value=r.metric_value,
            timestamp=r.timestamp,
            acknowledged=r.acknowledged,
        )
        for r in records
    ]


@router.post("/history/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: int, db: AsyncSession = Depends(get_db)):
    await db.execute(
        update(AlertHistory).where(AlertHistory.id == alert_id).values(acknowledged=True)
    )
    await db.commit()
    return {"status": "acknowledged"}