"""Celery task that dispatches inference to the GPU worker service."""

import httpx
import logging
from app.celery_app import celery
from app.core.config import get_settings

logger = logging.getLogger(__name__)


@celery.task(
    name="app.tasks.inference.run_inference",
    bind=True,
    max_retries=3,
    default_retry_delay=5,
)
def run_inference(self, symptoms: str, clinical_notes: str = "",
                  medical_history: dict | None = None,
                  patient_age: int | None = None,
                  patient_gender: str | None = None) -> dict:
    """
    Send inference request to the GPU worker service.
    Retries up to 3 times on failure.
    """
    settings = get_settings()
    inference_url = getattr(settings, "INFERENCE_WORKER_URL", "http://inference:8001")

    payload = {
        "symptoms": symptoms,
        "clinical_notes": clinical_notes,
        "medical_history": medical_history,
        "patient_age": patient_age,
        "patient_gender": patient_gender,
    }

    try:
        with httpx.Client(timeout=180.0) as client:
            response = client.post(f"{inference_url}/infer", json=payload)
            response.raise_for_status()
            result = response.json()
            logger.info(
                f"Inference completed: {result.get('diagnosis', 'unknown')} "
                f"({result.get('inference_time_ms', 0)}ms)"
            )
            return result
    except Exception as exc:
        logger.error(f"Inference failed (attempt {self.request.retries + 1}): {exc}")
        raise self.retry(exc=exc)
