import logging
import uuid

from sqlalchemy.orm import joinedload

from app.config import settings
from app.database import SessionLocal
from app.models.meeting import Meeting
from app.models.participant import MeetingParticipant
from app.services import notulen as notulen_service
from app.services.email import send_notulen_email
from app.services.pdf import generate_notulen_pdf
from app.worker import celery_app

logger = logging.getLogger(__name__)


@celery_app.task
def send_notulen_task(meeting_id: str, version: int):
    """Kirim email + PDF notulen ke semua peserta yang punya invitation token.

    Dipanggil setelah organizer publish / kirim ulang (bukan dari pipeline ML), supaya
    request HTTP tidak menunggu SMTP ke banyak peserta. PDF dibuat sekali lalu
    dipakai bersama; Message-ID/thread diatur di send_notulen_email.
    """
    db = SessionLocal()
    try:
        meeting = (
            db.query(Meeting)
            .options(
                joinedload(Meeting.participants).joinedload(MeetingParticipant.user),
                joinedload(Meeting.participants).joinedload(MeetingParticipant.invitation),
            )
            .filter(Meeting.id == uuid.UUID(meeting_id))
            .first()
        )
        if meeting is None or meeting.summary is None:
            logger.error("send_notulen_task: meeting %s atau notulennya tidak ditemukan", meeting_id)
            return

        organizer_name = meeting.organizer.name if meeting.organizer else "Organizer"
        pdf_bytes = generate_notulen_pdf(
            meeting=meeting,
            organizer_name=organizer_name,
            participants=meeting.participants,
            summary=meeting.summary,
            action_items=meeting.action_items,
            version_label=notulen_service.version_label(meeting),
        )

        for p in meeting.participants:
            if not p.invitation or not p.invitation.token:
                continue
            send_notulen_email(
                recipient_email=p.email,
                recipient_name=p.user.name if p.user else p.email,
                meeting_title=meeting.title,
                scheduled_at=meeting.scheduled_at,
                checkin_url=f"{settings.APP_BASE_URL}/check-in/{p.invitation.token}",
                pdf_bytes=pdf_bytes,
                meeting_id=meeting.id,
                db=db,
                participant_id=p.id,
                version=version,
            )
        db.commit()
    finally:
        db.close()
