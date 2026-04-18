"""
Compute and cache per-disease accuracy weights from diagnosis feedback.

Weights are stored in Redis and used by the knowledge graph scorer to
boost diseases the AI diagnoses correctly and dampen those it gets wrong.

Weight formula per disease:
  weight = 0.5 + (accuracy * 1.0)
  - accuracy = correct / total for that disease
  - weight ranges from 0.5 (0% accuracy) to 1.5 (100% accuracy)
  - diseases with no feedback get weight 1.0 (neutral)

Minimum 3 feedback samples required per disease to apply a weight.
"""

import json
import logging
import re
from typing import Any

logger = logging.getLogger("feedback_weights")

_REDIS_WEIGHTS_KEY = "meddiagnose:feedback_weights"
_REDIS_TTL = 3600  # 1 hour
_MIN_SAMPLES = 3


def _normalise(text: str) -> str:
    t = text.lower().strip()
    t = re.sub(r"[^a-z0-9\s]", "", t)
    return re.sub(r"\s+", " ", t)


async def compute_and_cache_weights(db_session) -> dict[str, float]:
    """
    Query diagnosis_feedback table, compute per-disease accuracy weights,
    and cache in Redis.

    Returns the weights dict.
    """
    from sqlalchemy import select, func, case
    from app.models.diagnosis_feedback import DiagnosisFeedback

    q = await db_session.execute(
        select(
            DiagnosisFeedback.ai_diagnosis_snapshot,
            func.count(DiagnosisFeedback.id),
            func.sum(case((DiagnosisFeedback.ai_was_correct == True, 1), else_=0)),
        )
        .where(DiagnosisFeedback.ai_diagnosis_snapshot.isnot(None))
        .group_by(DiagnosisFeedback.ai_diagnosis_snapshot)
        .having(func.count(DiagnosisFeedback.id) >= _MIN_SAMPLES)
    )

    weights: dict[str, float] = {}
    for disease_name, total, correct in q.all():
        accuracy = correct / total if total > 0 else 0
        # 0.5 + accuracy → range [0.5, 1.5]
        weight = 0.5 + accuracy
        weights[_normalise(disease_name)] = round(weight, 3)

    if weights:
        logger.info("Computed feedback weights for %d diseases", len(weights))
    else:
        logger.debug("No feedback weights computed (insufficient feedback data)")

    # Cache in Redis
    _cache_weights(weights)

    # Clear in-memory cache so next graph query picks up new weights
    from app.services.disease_knowledge_graph import invalidate_cache
    invalidate_cache()

    return weights


def _cache_weights(weights: dict[str, float]) -> None:
    """Store weights in Redis."""
    try:
        import redis
        from app.core.config import get_settings
        settings = get_settings()
        r = redis.from_url(settings.REDIS_URL, decode_responses=True)
        r.setex(_REDIS_WEIGHTS_KEY, _REDIS_TTL, json.dumps(weights))
    except Exception as e:
        logger.debug("Failed to cache feedback weights: %s", e)


async def refresh_weights() -> None:
    """Refresh feedback weights. Call periodically or after feedback submission."""
    from app.core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        await compute_and_cache_weights(db)
