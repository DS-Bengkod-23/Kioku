from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date
import uuid

from app.database import get_db
from app.services.auth import get_current_user
from app.models.user import User
from app.schemas.meeting import (
    MeetingCreate,
    MeetingUpdate,
    MeetingListResponse,
    MeetingDetail,
    MeetingDeletedNotice,
    RsvpRequest,
)
from app.schemas.action_item import ActionItemResponse, ActionItemCreateRequest
from app.services import meeting as meeting_service
from app.services import action_item as action_item_service
from app.services.pdf import generate_notulen_pdf

router = APIRouter(tags=["meetings"])


def _mask_others_checkin_tokens(meeting, detail: MeetingDetail, current_user_id: uuid.UUID) -> MeetingDetail:
    # checkin_token adalah magic link milik masing-masing peserta -- jangan
    # bocor ke peserta lain, hanya organizer dan peserta itu sendiri yang boleh melihatnya.
    if meeting.organizer_id != current_user_id:
        for participant, participant_detail in zip(meeting.participants, detail.participants):
            if participant.user_id != current_user_id:
                participant_detail.checkin_token = None
    return detail

@router.post("/", response_model=MeetingDetail, status_code=status.HTTP_201_CREATED)
def create_meeting(
    data: MeetingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return meeting_service.create_meeting(db, organizer_id=current_user.id, data=data)

@router.get("/", response_model=MeetingListResponse)
def get_meetings(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    status: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return meeting_service.get_meetings(
        db, user_id=current_user.id, page=page, limit=limit, status=status,
        date_from=date_from, date_to=date_to,
    )

@router.get("/search", response_model=MeetingListResponse)
def search_meetings(
    q: str,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return meeting_service.search_meetings(
        db, user_id=current_user.id, query=q, page=page, limit=limit,
        date_from=date_from, date_to=date_to,
    )

@router.get("/{meeting_id}", response_model=MeetingDetail | MeetingDeletedNotice)
def get_meeting(
    meeting_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    meeting = meeting_service.get_meeting(db, meeting_id=meeting_id, user_id=current_user.id)
    if meeting.deleted_at is not None:
        return MeetingDeletedNotice(id=meeting.id)
    detail = MeetingDetail.model_validate(meeting)
    return _mask_others_checkin_tokens(meeting, detail, current_user.id)

@router.patch("/{meeting_id}", response_model=MeetingDetail)
def update_meeting(
    meeting_id: uuid.UUID,
    data: MeetingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return meeting_service.update_meeting(db, meeting_id=meeting_id, user_id=current_user.id, data=data)

@router.patch("/{meeting_id}/complete", response_model=MeetingDetail)
def complete_meeting(
    meeting_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return meeting_service.complete_meeting(db, meeting_id=meeting_id, user_id=current_user.id)


@router.patch("/{meeting_id}/rsvp", response_model=MeetingDetail)
def rsvp_meeting(
    meeting_id: uuid.UUID,
    data: RsvpRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    meeting = meeting_service.submit_rsvp(
        db, meeting_id=meeting_id, user_id=current_user.id, response=data.response, reason=data.reason
    )
    detail = MeetingDetail.model_validate(meeting)
    return _mask_others_checkin_tokens(meeting, detail, current_user.id)


@router.delete("/{meeting_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_meeting(
    meeting_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    meeting_service.delete_meeting(db, meeting_id=meeting_id, user_id=current_user.id)


@router.post("/{meeting_id}/action-items", response_model=ActionItemResponse, status_code=status.HTTP_201_CREATED)
def create_action_item(
    meeting_id: uuid.UUID,
    data: ActionItemCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return action_item_service.create_action_item(db, meeting_id=meeting_id, user_id=current_user.id, data=data)


@router.get("/{meeting_id}/notulen.pdf")
def download_notulen_pdf(
    meeting_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verifikasi akses — throws 403/404 kalau user bukan peserta
    meeting = meeting_service.get_meeting(db, meeting_id=meeting_id, user_id=current_user.id)

    if meeting.summary is None:
        raise HTTPException(status_code=404, detail="Notulen belum tersedia")

    organizer_name = meeting.organizer.name if meeting.organizer else "Organizer"
    pdf_bytes = generate_notulen_pdf(
        meeting=meeting,
        organizer_name=organizer_name,
        participants=meeting.participants,
        summary=meeting.summary,
        action_items=meeting.action_items or [],
    )
    safe_title = "".join(c if c.isalnum() or c in " _-" else "_" for c in meeting.title)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="notulen-{safe_title}.pdf"'},
    )
