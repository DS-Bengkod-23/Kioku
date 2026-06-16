from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from typing import Optional
import uuid

from app.database import get_db
from app.services.auth import get_current_user
from app.models.user import User
from app.schemas.meeting import (
    MeetingCreate,
    MeetingUpdate,
    MeetingListResponse,
    MeetingDetail,
)
from app.services import meeting as meeting_service

router = APIRouter(tags=["meetings"])

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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return meeting_service.get_meetings(db, user_id=current_user.id, page=page, limit=limit, status=status)

@router.get("/search", response_model=MeetingListResponse)
def search_meetings(
    q: str,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return meeting_service.search_meetings(db, user_id=current_user.id, query=q, page=page, limit=limit)

@router.get("/{meeting_id}", response_model=MeetingDetail)
def get_meeting(
    meeting_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return meeting_service.get_meeting(db, meeting_id=meeting_id, user_id=current_user.id)

@router.patch("/{meeting_id}", response_model=MeetingDetail)
def update_meeting(
    meeting_id: uuid.UUID,
    data: MeetingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return meeting_service.update_meeting(db, meeting_id=meeting_id, user_id=current_user.id, data=data)

@router.delete("/{meeting_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_meeting(
    meeting_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    meeting_service.delete_meeting(db, meeting_id=meeting_id, user_id=current_user.id)
