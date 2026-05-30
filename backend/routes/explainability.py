from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone, timedelta

from database import get_db, ExplainabilityResult
from models.schemas import ExplainRequest, ExplainabilityResponse
from explainability.engine import explainability_engine

router = APIRouter(prefix="/api/v1/explain", tags=["Explainability"])


@router.post("/", response_model=ExplainabilityResponse)
async def explain_prediction(payload: ExplainRequest, db: AsyncSession = Depends(get_db)):
    """Generate explanation for a prediction instance."""
    if payload.method == "shap":
        result = explainability_engine.explain_shap(payload.model_id, payload.instance)
    elif payload.method == "lime":
        result = explainability_engine.explain_lime(payload.model_id, payload.instance)
    else:
        result = explainability_engine.explain_shap(payload.model_id, payload.instance)

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # Store result
    record = ExplainabilityResult(
        model_id=payload.model_id,
        prediction_id=payload.prediction_id,
        timestamp=now,
        method=result["method"],
        feature_importances=result["feature_importances"],
        explanation_details=result.get("explanation_details", {}),
    )
    db.add(record)
    await db.commit()

    return ExplainabilityResponse(
        method=result["method"],
        feature_importances=result["feature_importances"],
        explanation_details=result.get("explanation_details", {}),
        timestamp=now,
    )


@router.get("/{model_id}/history")
async def get_explanation_history(model_id: int, limit: int = 50, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ExplainabilityResult)
        .where(ExplainabilityResult.model_id == model_id)
        .order_by(ExplainabilityResult.timestamp.desc())
        .limit(limit)
    )
    records = result.scalars().all()
    return [
        ExplainabilityResponse(
            method=r.method,
            feature_importances=r.feature_importances,
            explanation_details=r.explanation_details or {},
            timestamp=r.timestamp,
        )
        for r in records
    ]