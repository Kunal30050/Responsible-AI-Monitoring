import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from database import init_db
from kafka_layer.consumer import start_consumers
from kafka_layer.producer import close_producer
from routes import monitoring, bias, drift, explainability, risk, alerts

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 Starting Responsible AI Monitoring Platform")
    await init_db()
    logger.info("✅ Database initialized")

    try:
        await start_consumers()
        logger.info("✅ Kafka consumers started")
    except Exception as e:
        logger.warning(f"⚠️ Kafka not available, running without streaming: {e}")

    yield

    # Shutdown
    await close_producer()
    logger.info("👋 Platform shutdown complete")


app = FastAPI(
    title="Responsible AI Monitoring Platform",
    description="Real-time monitoring for AI fairness, explainability, drift detection, and risk scoring",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(monitoring.router)
app.include_router(bias.router)
app.include_router(drift.router)
app.include_router(explainability.router)
app.include_router(risk.router)
app.include_router(alerts.router)


@app.get("/")
async def root():
    return {
        "name": "Responsible AI Monitoring Platform",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "models": "/api/v1/models",
            "bias": "/api/v1/bias",
            "drift": "/api/v1/drift",
            "explainability": "/api/v1/explain",
            "risk": "/api/v1/risk",
            "alerts": "/api/v1/alerts",
        }
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}