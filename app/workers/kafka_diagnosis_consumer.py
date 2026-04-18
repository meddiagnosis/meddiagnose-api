"""
Kafka consumer worker for parallel bulk diagnosis processing.

Run multiple instances for horizontal scaling. Each consumer processes
one diagnosis job at a time; N consumers = N parallel inferences.

Usage:
    cd backend
    KAFKA_ENABLED=true python -m app.workers.kafka_diagnosis_consumer

Or with Docker:
    docker run ... python -m app.workers.kafka_diagnosis_consumer
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("kafka_diagnosis_consumer")


def _symptoms_to_str(symptoms) -> str:
    if isinstance(symptoms, str):
        return symptoms
    if isinstance(symptoms, list):
        return ", ".join(str(s) for s in symptoms if s)
    return str(symptoms) if symptoms else ""


async def process_job(job: dict) -> dict | None:
    """Run MedGemma inference for one diagnosis job. Returns result or None on failure."""
    from app.core.config import get_settings

    diagnosis_id = job.get("diagnosis_id")
    symptoms = _symptoms_to_str(job.get("symptoms", ""))
    clinical_notes = job.get("clinical_notes") or ""
    medical_history = job.get("medical_history") or {}

    if not symptoms and not clinical_notes:
        logger.warning("Job %s has no symptoms or clinical_notes", diagnosis_id)
        return {"diagnosis_id": diagnosis_id, "error": "No symptoms or clinical notes"}

    settings = get_settings()
    use_vertex = getattr(settings, "KAFKA_USE_VERTEX_AI", False)

    try:
        if use_vertex:
            from app.services.vertex_ai_diagnosis import diagnose_vertex
            result = await asyncio.to_thread(
                diagnose_vertex,
                symptoms,
                clinical_notes,
                medical_history,
            )
        else:
            from app.services.medgemma_diagnosis import diagnose as medgemma_diagnose
            result = await medgemma_diagnose(symptoms, clinical_notes, medical_history)

        result["diagnosis_id"] = diagnosis_id
        result["patient_id"] = job.get("patient_id")
        result["batch_id"] = job.get("batch_id")
        return result
    except Exception as e:
        logger.exception("Inference failed for diagnosis %s: %s", diagnosis_id, e)
        return {"diagnosis_id": diagnosis_id, "error": str(e)}


def _update_diagnosis_in_db(diagnosis_id: int, result: dict) -> None:
    """Sync DB update for diagnosis result."""
    from sqlalchemy import create_engine, text
    from app.core.config import get_settings

    settings = get_settings()
    db_url = settings.DATABASE_URL_SYNC
    engine = create_engine(db_url)

    if "error" in result:
        with engine.connect() as conn:
            conn.execute(text("""
                UPDATE diagnoses SET status = 'queued', ai_reasoning = :err, updated_at = NOW()
                WHERE id = :did
            """), {"err": result["error"], "did": diagnosis_id})
            conn.commit()
        return

    import json as _json
    with engine.connect() as conn:
        conn.execute(text("""
            UPDATE diagnoses SET
                status = :status,
                ai_diagnosis = :diagnosis,
                ai_reasoning = :reasoning,
                ai_confidence = :confidence,
                ai_model_version = :model_version,
                ai_findings = :findings,
                ai_medications = :medications,
                ai_lifestyle = :lifestyle,
                ai_precautions = :precautions,
                ai_severity = :severity,
                ai_urgency = :urgency,
                ai_when_to_see_doctor = :when_to_see_doctor,
                ai_recommended_tests = :recommended_tests,
                ai_differential_diagnoses = :differentials,
                ai_raw_response = :raw_response,
                updated_at = NOW()
            WHERE id = :did
        """), {
            "status": "pending_review",
            "diagnosis": result.get("diagnosis", ""),
            "reasoning": result.get("reasoning", ""),
            "confidence": result.get("confidence", 0),
            "model_version": result.get("model_version", ""),
            "findings": _json.dumps(result.get("findings", [])),
            "medications": _json.dumps(result.get("medications", [])),
            "lifestyle": _json.dumps(result.get("lifestyle_recommendations", [])),
            "precautions": _json.dumps(result.get("precautions", [])),
            "severity": result.get("severity", "moderate"),
            "urgency": result.get("urgency", "soon"),
            "when_to_see_doctor": result.get("when_to_see_doctor", ""),
            "recommended_tests": _json.dumps(result.get("recommended_tests", [])),
            "differentials": _json.dumps(result.get("differential_diagnoses", [])),
            "raw_response": _json.dumps(result),
            "did": diagnosis_id,
        })
        conn.commit()
    logger.info("Updated diagnosis %s: %s", diagnosis_id, result.get("diagnosis", "")[:50])


def _update_batch_progress(batch_id: int, success: bool) -> None:
    """Increment batch processed_count or failed_count."""
    from sqlalchemy import create_engine, text
    from app.core.config import get_settings

    settings = get_settings()
    engine = create_engine(settings.DATABASE_URL_SYNC)
    col = "processed_count" if success else "failed_count"
    with engine.connect() as conn:
        conn.execute(text(f"""
            UPDATE batches SET {col} = {col} + 1, updated_at = NOW()
            WHERE id = :bid
        """), {"bid": batch_id})
        conn.commit()


async def consume_loop():
    """Main consumer loop."""
    from aiokafka import AIOKafkaConsumer
    from app.core.config import get_settings

    settings = get_settings()
    if not getattr(settings, "KAFKA_ENABLED", False):
        logger.error("KAFKA_ENABLED is not True. Set env KAFKA_ENABLED=true")
        sys.exit(1)

    consumer = AIOKafkaConsumer(
        settings.KAFKA_DIAGNOSIS_TOPIC,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id="meddiagnose-diagnosis-workers",
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        auto_offset_reset="earliest",
    )
    await consumer.start()
    logger.info("Consumer started: %s (group: meddiagnose-diagnosis-workers)", settings.KAFKA_DIAGNOSIS_TOPIC)

    try:
        async for msg in consumer:
            try:
                job = msg.value
                diagnosis_id = job.get("diagnosis_id")
                batch_id = job.get("batch_id")
                logger.info("Processing diagnosis %s (batch %s)", diagnosis_id, batch_id)

                result = await process_job(job)
                if result:
                    _update_diagnosis_in_db(diagnosis_id, result)
                    success = "error" not in result
                    if batch_id:
                        _update_batch_progress(batch_id, success)
            except Exception as e:
                logger.exception("Failed to process message: %s", e)
    finally:
        await consumer.stop()


def main():
    os.environ.setdefault("KAFKA_ENABLED", "true")
    asyncio.run(consume_loop())


if __name__ == "__main__":
    main()
