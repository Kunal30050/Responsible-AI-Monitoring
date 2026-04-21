import json
import asyncio
import logging
from aiokafka import AIOKafkaConsumer
from config import get_settings
from database import async_session, PredictionLog
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
settings = get_settings()


async def prediction_consumer():
    """Consumes prediction events from Kafka and stores them in the database."""
    consumer = AIOKafkaConsumer(
        settings.KAFKA_TOPIC_PREDICTIONS,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id=settings.KAFKA_CONSUMER_GROUP,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        auto_offset_reset="latest",
    )

    await consumer.start()
    logger.info("Kafka prediction consumer started")

    try:
        async for message in consumer:
            data = message.value
            try:
                async with async_session() as session:
                    log_entry = PredictionLog(
                        model_id=data["model_id"],
                        timestamp=datetime.fromisoformat(data.get("timestamp", datetime.now(timezone.utc).isoformat())),
                        features=data["features"],
                        prediction=data["prediction"],
                        actual=data.get("actual"),
                        protected_attributes=data.get("protected_attributes", {}),
                    )
                    session.add(log_entry)
                    await session.commit()
            except Exception as e:
                logger.error(f"Error processing prediction message: {e}")
    finally:
        await consumer.stop()


async def start_consumers():
    """Start all Kafka consumers as background tasks."""
    asyncio.create_task(prediction_consumer())