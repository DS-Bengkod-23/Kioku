from celery import Celery
from app.config import settings

celery_app = Celery(
    "kioku",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.process_recording", "app.tasks.calendar_sync"],
)
