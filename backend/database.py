from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, JSON, Boolean, Text, Enum as SAEnum
)
from datetime import datetime, timezone
import enum

from config import get_settings

settings = get_settings()

engine = create_async_engine(settings.DATABASE_URL, echo=False, pool_size=20)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


# ── Enums ────────────────────────────────────────
class AlertSeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertChannel(str, enum.Enum):
    SLACK = "slack"
    PAGERDUTY = "pagerduty"
    EMAIL = "email"


# ── ORM Models ───────────────────────────────────
class MonitoredModel(Base):
    __tablename__ = "monitored_models"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False)
    model_type = Column(String(100))  # classification, regression
    description = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True)
    metadata_ = Column("metadata", JSON, default=dict)


class PredictionLog(Base):
    __tablename__ = "prediction_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_id = Column(Integer, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    features = Column(JSON, nullable=False)
    prediction = Column(Float, nullable=False)
    actual = Column(Float, nullable=True)
    protected_attributes = Column(JSON, default=dict)  # e.g., {"gender": 1, "race": 0}


class BiasMetric(Base):
    __tablename__ = "bias_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_id = Column(Integer, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    metric_name = Column(String(100))  # disparate_impact, equalized_odds, etc.
    protected_attribute = Column(String(100))
    privileged_value = Column(String(50))
    unprivileged_value = Column(String(50))
    metric_value = Column(Float)
    is_fair = Column(Boolean)
    details = Column(JSON, default=dict)


class DriftMetric(Base):
    __tablename__ = "drift_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_id = Column(Integer, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    drift_type = Column(String(50))  # data_drift, concept_drift, prediction_drift
    feature_name = Column(String(100))
    statistic_name = Column(String(100))  # ks_test, psi, wasserstein
    statistic_value = Column(Float)
    p_value = Column(Float, nullable=True)
    is_drifted = Column(Boolean)
    details = Column(JSON, default=dict)


class ExplainabilityResult(Base):
    __tablename__ = "explainability_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_id = Column(Integer, nullable=False)
    prediction_id = Column(Integer, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    method = Column(String(50))  # shap, lime, alibi
    feature_importances = Column(JSON)
    explanation_details = Column(JSON, default=dict)


class RiskScore(Base):
    __tablename__ = "risk_scores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_id = Column(Integer, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    overall_score = Column(Float)
    bias_score = Column(Float)
    drift_score = Column(Float)
    performance_score = Column(Float)
    explainability_score = Column(Float)
    risk_level = Column(String(20))  # low, medium, high, critical
    details = Column(JSON, default=dict)


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    model_id = Column(Integer, nullable=True)  # null = all models
    metric_type = Column(String(50))  # bias, drift, risk, performance
    condition = Column(String(20))  # gt, lt, eq, gte, lte
    threshold = Column(Float)
    severity = Column(SAEnum(AlertSeverity), default=AlertSeverity.MEDIUM)
    channels = Column(JSON, default=list)  # ["slack", "email"]
    is_active = Column(Boolean, default=True)
    cooldown_minutes = Column(Integer, default=30)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class AlertHistory(Base):
    __tablename__ = "alert_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rule_id = Column(Integer, nullable=False)
    model_id = Column(Integer, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    severity = Column(SAEnum(AlertSeverity))
    message = Column(Text)
    metric_value = Column(Float)
    channels_notified = Column(JSON, default=list)
    acknowledged = Column(Boolean, default=False)


# ── TimescaleDB Hypertable Setup ─────────────────
# We convert time-series tables to hypertables for efficient time-range queries
HYPERTABLE_SQL = """
SELECT create_hypertable('prediction_logs', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('bias_metrics', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('drift_metrics', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('risk_scores', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('alert_history', 'timestamp', if_not_exists => TRUE);
"""


async def init_db():
    """Create all tables and convert to hypertables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Setup TimescaleDB hypertables
    async with async_session() as session:
        for stmt in HYPERTABLE_SQL.strip().split("\n"):
            stmt = stmt.strip()
            if stmt:
                try:
                    await session.execute(
                        __import__("sqlalchemy").text(stmt)
                    )
                except Exception:
                    pass  # Hypertable already exists or TimescaleDB not available
        await session.commit()


async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session