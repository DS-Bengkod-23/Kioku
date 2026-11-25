import uuid
from fastapi import APIRouter, Depends, File, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.auth import get_current_user
from app.models.user import User
from app.schemas.recording import RecordingResponse, ProcessingStatusResponse
from app.schemas.recording_session import (
    ChunkResponse,
    FinishSessionRequest,
    SessionStatusResponse,
    StartSessionRequest,
    StartSessionResponse,
)
from app.services import recording as recording_service
from app.services import recording_session as session_service

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


@router.get("/{meeting_id}/recording/audio")
def get_recording_audio(
    meeting_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    chunks, content_type, size = recording_service.get_recording_audio(db, meeting_id, current_user.id)
    return StreamingResponse(
        chunks,
        media_type=content_type,
        headers={"Content-Length": str(size)},
    )


@router.post(
    "/{meeting_id}/recording/sessions",
    response_model=StartSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def start_recording_session(
    meeting_id: uuid.UUID,
    payload: StartSessionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = session_service.start_session(db, meeting_id, current_user.id, payload.mime_type)
    return StartSessionResponse(session_id=session.id, status=session.status)


@router.put(
    "/{meeting_id}/recording/sessions/{session_id}/chunks/{index}",
    response_model=ChunkResponse,
)
async def put_recording_chunk(
    meeting_id: uuid.UUID,
    session_id: uuid.UUID,
    index: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Badan permintaan = byte audio mentah (bukan multipart); satu potongan kecil,
    # jadi aman dibaca utuh ke memori.
    data = await request.body()
    chunk_count = session_service.store_chunk(db, meeting_id, session_id, current_user.id, index, data)
    return ChunkResponse(chunk_count=chunk_count)


@router.post(
    "/{meeting_id}/recording/sessions/{session_id}/finish",
    response_model=SessionStatusResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def finish_recording_session(
    meeting_id: uuid.UUID,
    session_id: uuid.UUID,
    payload: FinishSessionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = session_service.finish_session(db, meeting_id, session_id, current_user.id, payload.total_chunks)
    return SessionStatusResponse(
        session_id=session.id,
        status=session.status,
        chunk_count=session.chunk_count,
        error_message=session.error_message,
    )


@router.get(
    "/{meeting_id}/recording/sessions/{session_id}",
    response_model=SessionStatusResponse,
)
def get_recording_session(
    meeting_id: uuid.UUID,
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = session_service.get_session(db, meeting_id, session_id, current_user.id)
    return SessionStatusResponse(
        session_id=session.id,
        status=session.status,
        chunk_count=session.chunk_count,
        error_message=session.error_message,
    )


@router.delete("/{meeting_id}/recording", status_code=status.HTTP_204_NO_CONTENT)
def delete_recording(
    meeting_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    recording_service.delete_recording(db, meeting_id, current_user.id)
