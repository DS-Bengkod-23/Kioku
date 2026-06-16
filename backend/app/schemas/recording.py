from pydantic import BaseModel, model_validator
from typing import Optional, Any
from datetime import datetime
from uuid import UUID


class RecordingResponse(BaseModel):
    id: UUID
    file_url: str
    duration: Optional[float] = None
    size: int
    uploaded_at: datetime
    processing_status: str

    @model_validator(mode="before")
    @classmethod
    def extract_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            return data
        status = data.processing_status
        if hasattr(status, "value"):
            status = status.value
        return {
            "id": data.id,
            "file_url": data.file_url,
            "duration": data.duration,
            "size": data.size,
            "uploaded_at": data.uploaded_at,
            "processing_status": status,
        }


class ProcessingStatusResponse(BaseModel):
    processing_status: str
    steps: Optional[dict] = None
    error: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def extract_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            return data
        status = data.processing_status
        if hasattr(status, "value"):
            status = status.value
        return {
            "processing_status": status,
            "steps": data.processing_steps,
            "error": data.error_message,
        }
