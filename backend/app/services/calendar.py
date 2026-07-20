import uuid
import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
import requests
from sqlalchemy.orm import Session
from app.config import settings
from app.models.calendar_credential import GoogleCalendarCredential
from app.services.crypto import encrypt_token, decrypt_token
from app.services.auth import create_calendar_state_token, decode_calendar_state_token
from app.schemas.calendar import CalendarStatusResponse

logger = logging.getLogger(__name__)

TOKEN_URL = "https://oauth2.googleapis.com/token"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar.events"


def build_authorization_url(user_id: uuid.UUID) -> str:
    state = create_calendar_state_token(user_id)
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_CALENDAR_REDIRECT_URI,
        "response_type": "code",
        "scope": CALENDAR_SCOPE,
        # access_type=offline supaya Google balikin refresh_token, bukan cuma
        # access_token jangka pendek. prompt=consent memaksa Google tetap
        # mengirim refresh_token walau user sudah pernah authorize sebelumnya
        # (tanpa ini, authorize kedua kalinya bisa datang tanpa refresh_token).
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return f"{AUTH_URL}?{urlencode(params)}"


def handle_oauth_callback(db: Session, code: str, state: str) -> None:
    user_id = decode_calendar_state_token(state)

    resp = requests.post(
        TOKEN_URL,
        data={
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_CALENDAR_REDIRECT_URI,
            "grant_type": "authorization_code",
        },
        timeout=10,
    )
    resp.raise_for_status()
    token_data = resp.json()

    cred = db.query(GoogleCalendarCredential).filter(
        GoogleCalendarCredential.user_id == user_id
    ).first()
    if cred is None:
        cred = GoogleCalendarCredential(user_id=user_id)
        db.add(cred)

    cred.access_token = encrypt_token(token_data["access_token"])
    # refresh_token cuma dikirim Google kalau prompt=consent (lihat komentar di
    # build_authorization_url) -- kalau karena suatu sebab tetap kosong, pertahankan
    # refresh_token lama daripada menimpanya dengan kosong.
    if token_data.get("refresh_token"):
        cred.refresh_token = encrypt_token(token_data["refresh_token"])
    cred.token_expiry = datetime.now(timezone.utc) + timedelta(seconds=token_data.get("expires_in", 3600))
    cred.connected = True
    db.commit()


def get_calendar_status(db: Session, user_id: uuid.UUID) -> CalendarStatusResponse:
    cred = db.query(GoogleCalendarCredential).filter(
        GoogleCalendarCredential.user_id == user_id
    ).first()
    if not cred or not cred.connected:
        return CalendarStatusResponse(connected=False)
    return CalendarStatusResponse(connected=True, connected_at=cred.created_at)


def disconnect_calendar(db: Session, user_id: uuid.UUID) -> None:
    # Cuma hapus kredensialnya -- event yang sudah ke-sync sebelumnya sengaja
    # dibiarkan apa adanya di Google Calendar user, tidak ikut dihapus otomatis.
    db.query(GoogleCalendarCredential).filter(
        GoogleCalendarCredential.user_id == user_id
    ).delete()
    db.commit()


def get_valid_access_token(db: Session, cred: GoogleCalendarCredential) -> str | None:
    """Balikin access_token yang masih berlaku, refresh dulu kalau sudah/hampir
    expired. Balikin None (dan tandai cred.connected=False) kalau refresh_token
    sudah dicabut user dari sisi Google (invalid_grant) -- caller wajib skip
    sync untuk kredensial ini, bukan retry."""
    if cred.token_expiry and cred.token_expiry > datetime.now(timezone.utc) + timedelta(seconds=60):
        return decrypt_token(cred.access_token)

    if not cred.refresh_token:
        cred.connected = False
        db.commit()
        return None

    resp = requests.post(
        TOKEN_URL,
        data={
            "refresh_token": decrypt_token(cred.refresh_token),
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "grant_type": "refresh_token",
        },
        timeout=10,
    )
    if resp.status_code == 400 and resp.json().get("error") == "invalid_grant":
        logger.warning("Google Calendar refresh token invalid_grant untuk user %s, marking disconnected", cred.user_id)
        cred.connected = False
        db.commit()
        return None
    resp.raise_for_status()

    token_data = resp.json()
    cred.access_token = encrypt_token(token_data["access_token"])
    cred.token_expiry = datetime.now(timezone.utc) + timedelta(seconds=token_data.get("expires_in", 3600))
    db.commit()
    return token_data["access_token"]
