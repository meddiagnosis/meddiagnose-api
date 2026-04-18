"""
Kafka producer for bulk diagnosis jobs.

Publishes diagnosis job messages to a Kafka topic. Multiple consumer workers
can process jobs in parallel for scalable bulk inference.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger("kafka_producer")

_producer = None


async def get_producer():
    """Lazy-init AIOKafkaProducer. Call close_producer() on shutdown."""
    global _producer
    if _producer is not None:
        return _producer
    settings = get_settings()
    if not getattr(settings, "KAFKA_ENABLED", False):
        return None
    try:
        from aiokafka import AIOKafkaProducer
        _producer = AIOKafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
        await _producer.start()
        logger.info("Kafka producer started: %s", settings.KAFKA_BOOTSTRAP_SERVERS)
        return _producer
    except Exception as e:
        logger.warning("Kafka producer init failed: %s", e)
        return None


async def close_producer():
    """Shutdown Kafka producer."""
    global _producer
    if _producer:
        await _producer.stop()
        _producer = None
        logger.info("Kafka producer stopped")


async def publish_diagnosis_job(job: dict[str, Any]) -> bool:
    """
    Publish a single diagnosis job to the Kafka topic.
    job: {diagnosis_id, patient_id, batch_id, symptoms, clinical_notes, medical_history, priority}
    """
    settings = get_settings()
    if not getattr(settings, "KAFKA_ENABLED", False):
        return False
    producer = await get_producer()
    if not producer:
        return False
    try:
        topic = settings.KAFKA_DIAGNOSIS_TOPIC
        await producer.send_and_wait(topic, value=job)
        logger.debug("Published diagnosis job %s to %s", job.get("diagnosis_id"), topic)
        return True
    except Exception as e:
        logger.error("Kafka publish failed: %s", e)
        return False


async def publish_batch_jobs(jobs: list[dict[str, Any]]) -> int:
    """Publish multiple diagnosis jobs. Returns count of successfully published."""
    settings = get_settings()
    if not getattr(settings, "KAFKA_ENABLED", False):
        return 0
    producer = await get_producer()
    if not producer:
        return 0
    topic = settings.KAFKA_DIAGNOSIS_TOPIC
    count = 0
    for job in jobs:
        try:
            await producer.send_and_wait(topic, value=job)
            count += 1
        except Exception as e:
            logger.error("Kafka publish failed for job %s: %s", job.get("diagnosis_id"), e)
    return count
