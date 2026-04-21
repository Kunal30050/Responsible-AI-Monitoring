from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://raiuser:raipassword@localhost:5432/rai_platform"

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_TOPIC_PREDICTIONS: str = "model-predictions"
    KAFKA_TOPIC_METRICS: str = "monitoring-metrics"
    KAFKA_CONSUMER_GROUP: str = "rai-monitor-group"

    # Alerting
    SLACK_WEBHOOK_URL: str = ""
    PAGERDUTY_API_KEY: str = ""
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    ALERT_EMAIL_TO: str = ""

    # Thresholds
    BIAS_THRESHOLD: float = 0.1
    DRIFT_THRESHOLD: float = 0.05
    RISK_THRESHOLD: float = 0.7

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()