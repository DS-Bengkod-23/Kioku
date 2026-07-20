import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models.user import User
from app.services.auth import get_current_user, get_current_user_from_cookie
from app.schemas.calendar import CalendarStatusResponse
from app.services import calendar as calendar_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["calendar"])


@router.get("/auth/google/calendar/connect")
def connect_calendar(request: Request, db: Session = Depends(get_db)):
    if not settings.GOOGLE_CALENDAR_SYNC_ENABLED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")
    user = get_current_user_from_cookie(request, db)
    url = calendar_service.build_authorization_url(user.id)
    return RedirectResponse(url)


@router.get("/auth/google/calendar/callback")
def calendar_callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    db: Session = Depends(get_db),
):
    redirect_base = f"{settings.APP_BASE_URL}/profile"
    if error or not code or not state:
        return RedirectResponse(f"{redirect_base}?calendar=error")
    try:
        calendar_service.handle_oauth_callback(db, code=code, state=state)
    except Exception:
        logger.exception("Gagal menyelesaikan Google Calendar OAuth callback")
        return RedirectResponse(f"{redirect_base}?calendar=error")
    return RedirectResponse(f"{redirect_base}?calendar=connected")


@router.get("/me/calendar-status", response_model=CalendarStatusResponse)
def calendar_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return calendar_service.get_calendar_status(db, current_user.id)


@router.delete("/auth/google/calendar", response_model=CalendarStatusResponse)
def disconnect_calendar(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    calendar_service.disconnect_calendar(db, current_user.id)
    return CalendarStatusResponse(connected=False)
