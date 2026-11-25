from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class StartSessionRequest(BaseModel):
    # Tipe MIME yang dipilih browser, mis. "audio/webm;codecs=opus".
    mime_type: str


class StartSessionResponse(BaseModel):
    session_id: UUID
    status: str


class FinishSessionRequest(BaseModel):
    total_chunks: int


class ChunkResponse(BaseModel):
    chunk_count: int


class SessionStatusResponse(BaseModel):
    session_id: UUID
    status: str
    chunk_count: int
    error_message: Optional[str] = None
