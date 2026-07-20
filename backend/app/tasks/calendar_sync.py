import uuid
import logging
from datetime import timedelta
import requests
from sqlalchemy.orm import Session, joinedload

from app.worker import celery_app
from app.database import SessionLocal
from app.config import settings
from app.models.meeting import Meeting
from app.models.participant import MeetingParticipant
from app.models.calendar_credential import GoogleCalendarCredential
from app.models.calendar_sync_event import CalendarSyncEvent
from app.services.calendar import get_valid_access_token

logger = logging.getLogger(__name__)

EVENTS_BASE_URL = "https://www.googleapis.com/calendar/v3/calendars/primary/events"


def _build_event_body(meeting: Meeting) -> dict:
    end = meeting.scheduled_at + timedelta(minutes=meeting.duration_minutes)
    return {
        "summary": meeting.title,
        # Cuma logistik (waktu/lokasi) yang dikirim ke Google -- agenda_text/
        # description meeting sengaja TIDAK disertakan (keputusan privasi, lihat
        # plan/handoff-google-integration.md).
        "location": meeting.location or "",
        "start": {"dateTime": meeting.scheduled_at.isoformat()},
        "end": {"dateTime": end.isoformat()},
    }


def _sync_one_participant(
    db: Session, meeting: Meeting, participant: MeetingParticipant, cred: GoogleCalendarCredential
) -> None:
    access_token = get_valid_access_token(db, cred)
    if not access_token:
        return  # refresh token sudah dicabut user, get_valid_access_token sudah menandai connected=False

    headers = {"Authorization": f"Bearer {access_token}"}
    body = _build_event_body(meeting)

    sync_event = db.query(CalendarSyncEvent).filter(
        CalendarSyncEvent.meeting_participant_id == participant.id
    ).first()

    if sync_event:
        resp = requests.patch(
            f"{EVENTS_BASE_URL}/{sync_event.google_event_id}", json=body, headers=headers, timeout=10
        )
        if resp.status_code == 404:
            # User menghapus event ini manual dari Google Calendar-nya sendiri --
            # buat ulang sebagai event baru daripada gagal diam-diam.
            db.delete(sync_event)
            db.flush()
            sync_event = None
        else:
            resp.raise_for_status()

    if not sync_event:
        resp = requests.post(EVENTS_BASE_URL, json=body, headers=headers, timeout=10)
        resp.raise_for_status()
        db.add(CalendarSyncEvent(meeting_participant_id=participant.id, google_event_id=resp.json()["id"]))

    db.commit()


@celery_app.task(bind=True, max_retries=3, retry_backoff=30, retry_backoff_max=300)
def sync_meeting_calendar_task(self, meeting_id: str):
    """Upsert event Calendar untuk semua participant meeting yang sudah connect.
    Dipanggil setelah create_meeting()/update_meeting() commit -- meng-cover
    keduanya sekaligus (participant baru => insert, yang sudah ada => patch)."""
    if not settings.GOOGLE_CALENDAR_SYNC_ENABLED:
        return
    db = SessionLocal()
    try:
        meeting = (
            db.query(Meeting)
            .options(joinedload(Meeting.participants))
            .filter(Meeting.id == uuid.UUID(meeting_id))
            .first()
        )
        if not meeting:
            return

        for p in meeting.participants:
            if not p.user_id:
                continue
            cred = db.query(GoogleCalendarCredential).filter(
                GoogleCalendarCredential.user_id == p.user_id,
                GoogleCalendarCredential.connected.is_(True),
            ).first()
            if not cred:
                continue
            try:
                _sync_one_participant(db, meeting, p, cred)
            except Exception:
                # Satu participant gagal (mis. rate limit sesaat) tidak boleh
                # menggagalkan sync participant lain di meeting yang sama.
                db.rollback()
                logger.exception(
                    "Gagal sync event Calendar meeting %s untuk user %s", meeting_id, p.user_id
                )
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3, retry_backoff=30, retry_backoff_max=300)
def delete_meeting_calendar_events_task(self, events: list[dict]):
    """events: [{"user_id": str, "google_event_id": str}, ...] -- di-snapshot oleh
    delete_meeting() SEBELUM meeting row (dan MeetingParticipant-nya) dihapus,
    karena setelah dihapus google_event_id tidak bisa diambil lagi dari DB."""
    if not settings.GOOGLE_CALENDAR_SYNC_ENABLED or not events:
        return
    db = SessionLocal()
    try:
        for item in events:
            cred = db.query(GoogleCalendarCredential).filter(
                GoogleCalendarCredential.user_id == uuid.UUID(item["user_id"]),
                GoogleCalendarCredential.connected.is_(True),
            ).first()
            if not cred:
                continue
            try:
                access_token = get_valid_access_token(db, cred)
                if not access_token:
                    continue
                resp = requests.delete(
                    f"{EVENTS_BASE_URL}/{item['google_event_id']}",
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=10,
                )
                if resp.status_code not in (200, 204, 404, 410):
                    resp.raise_for_status()
            except Exception:
                db.rollback()
                logger.exception("Gagal hapus event Calendar %s", item["google_event_id"])
    finally:
        db.close()
