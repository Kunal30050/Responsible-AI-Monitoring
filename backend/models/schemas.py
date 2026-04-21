from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum


# ── Enums ──────────────────────────────────
class ModelType(str, Enum):
    CLASSIFICATION = "classification"
    REGRESSION = "regression"


class DriftType(str, Enum):
    DATA_DRIFT = "data_drift"
    CONCEPT_DRIFT = "concept_drift"
    PREDICTION_DRIFT = "prediction_drift"


class SeverityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ── Request Models ─────────────────────────
class ModelRegistration(BaseModel):
    name: str
    model_type: ModelType
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class PredictionInput(BaseModel):
    model_id: int
    features: Dict[str, float]
    prediction: float
    actual: Optional[float] = None
    protected_attributes: Optional[Dict[str, Any]] = {}


class BatchPredictionInput(BaseModel):
    predictions: List[PredictionInput]


class BiasAnalysisRequest(BaseModel):
    model_id: int
    protected_attribute: str
    privileged_value: Any
    unprivileged_value: Any
    lookback_hours: int = 24


class DriftAnalysisRequest(BaseModel):
    model_id: int
    reference_window_hours: int = 168  # 7 days
    current_window_hours: int = 24
    features: Optional[List[str]] = None


class ExplainRequest(BaseModel):
    model_id: int
    prediction_id: Optional[int] = None
    instance: Dict[str, float]
    method: str = "shap"  # shap, lime


class AlertRuleCreate(BaseModel):
    name: str
    model_id: Optional[int] = None
    metric_type: str
    condition: str = "gt"
    threshold: float
    severity: SeverityLevel = SeverityLevel.MEDIUM
    channels: List[str] = ["slack"]
    cooldown_minutes: int = 30


# ── Response Models ────────────────────────
class ModelResponse(BaseModel):
    id: int
    name: str
    model_type: str
    description: Optional[str]
    created_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


class BiasMetricResponse(BaseModel):
    metric_name: str
    protected_attribute: str
    metric_value: float
    is_fair: bool
    timestamp: datetime
    details: Dict[str, Any] = {}


class DriftMetricResponse(BaseModel):
    feature_name: str
    drift_type: str
    statistic_name: str
    statistic_value: float
    p_value: Optional[float]
    is_drifted: bool
    timestamp: datetime


class ExplainabilityResponse(BaseModel):
    method: str
    feature_importances: Dict[str, float]
    explanation_details: Dict[str, Any] = {}
    timestamp: datetime


class RiskScoreResponse(BaseModel):
    model_id: int
    overall_score: float
    bias_score: float
    drift_score: float
    performance_score: float
    explainability_score: float
    risk_level: str
    timestamp: datetime
    details: Dict[str, Any] = {}


class AlertHistoryResponse(BaseModel):
    id: int
    rule_id: int
    model_id: int
    severity: str
    message: str
    metric_value: float
    timestamp: datetime
    acknowledged: bool


class DashboardSummary(BaseModel):
    total_models: int
    total_predictions_24h: int
    active_alerts: int
    avg_risk_score: float
    bias_issues: int
    drift_detected: int
    models: List[Dict[str, Any]]