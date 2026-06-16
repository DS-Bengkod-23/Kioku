import uuid
from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.auth import get_current_user
from app.models.user import User
from app.schemas.recording import RecordingResponse, ProcessingStatusResponse
from app.services import recording as recording_service

router = APIRouter(tags=["recordings"])


@router.post(
    "/{meeting_id}/recording",
    response_model=RecordingResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_recording(
    meeting_id: uuid.UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await recording_service.upload_recording(db, meeting_id, current_user.id, file)


@router.get("/{meeting_id}/recording/status", response_model=ProcessingStatusResponse)
def get_recording_status(
    meeting_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return recording_service.get_recording_status(db, meeting_id, current_user.id)


@router.delete("/{meeting_id}/recording", status_code=status.HTTP_204_NO_CONTENT)
def delete_recording(
    meeting_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    recording_service.delete_recording(db, meeting_id, current_user.id)
