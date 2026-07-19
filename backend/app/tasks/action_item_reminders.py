import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy.orm import joinedload

from app.worker import celery_app
from app.database import SessionLocal
from app.config import settings
from app.models.action_item import ActionItem, ActionItemStatus
from app.models.participant import MeetingParticipant
from app.services.email import send_action_item_reminder_email

logger = logging.getLogger(__name__)


@celery_app.task(bind=True)
def send_action_item_reminders_task(self):
    """Celery Beat job harian (lihat beat_schedule di worker.py): kirim email
    reminder untuk action item ber-status 'open' yang due besok. reminder_sent_at
    dipakai sebagai guard idempotency -- kalau Beat sempat jalan lebih dari
    sekali per hari (restart worker, dll), assignee yang sudah dikirimi tidak
    di-spam ulang."""
    db = SessionLocal()
    try:
        tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).date()

        items = (
            db.query(ActionItem)
            .options(
                joinedload(ActionItem.assignee_participant).joinedload(MeetingParticipant.user),
                joinedload(ActionItem.assignee_participant).joinedload(MeetingParticipant.invitation),
                joinedload(ActionItem.meeting),
            )
            .filter(
                ActionItem.due_date == tomorrow,
                ActionItem.status == ActionItemStatus.open,
                ActionItem.reminder_sent_at.is_(None),
                ActionItem.assignee_participant_id.isnot(None),
            )
            .all()
        )

        for item in items:
            participant = item.assignee_participant
            if not participant:
                continue

            recipient_email = participant.user.email if participant.user else participant.email
            recipient_name = participant.user.name if participant.user else participant.email

            if participant.invitation and participant.invitation.token:
                action_url = f"{settings.APP_BASE_URL}/check-in/{participant.invitation.token}"
            else:
                action_url = f"{settings.APP_BASE_URL}/action-items"

            try:
                send_action_item_reminder_email(
                    recipient_email=recipient_email,
                    recipient_name=recipient_name,
                    task=item.task,
                    due_date=item.due_date,
                    meeting_title=item.meeting.title if item.meeting else "",
                    action_url=action_url,
                )
                item.reminder_sent_at = datetime.now(timezone.utc)
                db.commit()
            except Exception:
                # Satu email gagal (mis. SMTP sesaat down) tidak boleh menggagalkan
                # reminder assignee lain di batch yang sama -- reminder_sent_at
                # sengaja tidak diisi supaya item ini otomatis dicoba lagi besok.
                db.rollback()
                logger.exception("Gagal mengirim reminder action item %s", item.id)
    finally:
        db.close()
