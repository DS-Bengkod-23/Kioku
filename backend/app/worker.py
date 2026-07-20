from celery import Celery
from celery.schedules import crontab
from app.config import settings

celery_app = Celery(
    "kioku",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.process_recording",
        "app.tasks.calendar_sync",
        "app.tasks.action_item_reminders",
    ],
)

celery_app.conf.timezone = "UTC"
celery_app.conf.beat_schedule = {
    "send-action-item-reminders-daily": {
        "task": "app.tasks.action_item_reminders.send_action_item_reminders_task",
        # Jam 8 pagi UTC -- sesuai draft di plan/feature-ideas.md #3.
        "schedule": crontab(hour=8, minute=0),
    },
}
