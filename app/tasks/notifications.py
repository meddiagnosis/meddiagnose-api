"""Celery task for async push notification delivery."""

import logging
from app.celery_app import celery

logger = logging.getLogger(__name__)


@celery.task(name="app.tasks.notifications.send_push_notification")
def send_push_notification(user_id: int, title: str, body: str, data: dict | None = None):
    """
    Send a push notification to a user's device.
    In production, integrate with Firebase Cloud Messaging (FCM) or Expo Push Service.
    """
    logger.info(f"Push notification -> user {user_id}: {title}")

    try:
        import httpx
        expo_push_url = "https://exp.host/--/api/v2/push/send"
        # In production, look up the user's Expo push token from the database
        # For now, log and return success
        logger.info(f"Would send to Expo Push API: title='{title}', body='{body}'")
        return {"status": "sent", "user_id": user_id}
    except Exception as e:
        logger.error(f"Push notification failed for user {user_id}: {e}")
        return {"status": "failed", "error": str(e)}
