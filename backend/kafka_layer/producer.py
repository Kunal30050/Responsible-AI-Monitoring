import json
import asyncio
from aiokafka import AIOKafkaProducer
from config import get_settings

settings = get_settings()

_producer: AIOKafkaProducer = None


async def get_producer() -> AIOKafkaProducer:
    global _producer
    if _producer is None:
        _producer = AIOKafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
        )
        await _producer.start()
    return _producer


async def send_prediction(data: dict):
    producer = await get_producer()
    await producer.send_and_wait(settings.KAFKA_TOPIC_PREDICTIONS, data)


async def send_metric(data: dict):
    producer = await get_producer()
    await producer.send_and_wait(settings.KAFKA_TOPIC_METRICS, data)


async def close_producer():
    global _producer
    if _producer:
        await _producer.stop()
        _producer = None