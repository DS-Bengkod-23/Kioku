import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.notulen import (
    NotulenMeta,
    SpeakerRenameRequest,
    SummaryResponse,
    SummaryUpdateRequest,
    TranscriptResponse,
)
from app.services import notulen as notulen_service
from app.services.auth import get_current_user

router = APIRouter(tags=["notulen"])


@router.patch("/{meeting_id}/summary", response_model=SummaryResponse)
def update_summary(
    meeting_id: uuid.UUID,
    data: SummaryUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return notulen_service.update_summary(db, meeting_id, current_user.id, data)


@router.patch("/{meeting_id}/transcript/speakers", response_model=TranscriptResponse)
def rename_speakers(
    meeting_id: uuid.UUID,
    data: SpeakerRenameRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return notulen_service.rename_speakers(db, meeting_id, current_user.id, data.renames)


@router.post("/{meeting_id}/notulen/publish", response_model=NotulenMeta)
def publish_notulen(
    meeting_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    meeting = notulen_service.publish_notulen(db, meeting_id, current_user.id)
    return notulen_service.build_notulen_meta(meeting)


@router.post("/{meeting_id}/notulen/resend", response_model=NotulenMeta)
def resend_notulen(
    meeting_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    meeting = notulen_service.resend_notulen(db, meeting_id, current_user.id)
    return notulen_service.build_notulen_meta(meeting)
