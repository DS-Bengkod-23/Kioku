import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class NotulenMeta(BaseModel):
    """Status editorial notulen, diturunkan dari Meeting + notulen_versions."""

    status: Optional[Literal["draft", "published"]] = None
    current_version: Optional[int] = None
    last_published_at: Optional[datetime] = None
    edited_at: Optional[datetime] = None
    has_unsent_changes: bool = False
    needs_review_count: int = 0


def _clean_items(items: list[str] | None) -> list[str] | None:
    if items is None:
        return None
    return [stripped for item in items if (stripped := item.strip())]


class SummaryUpdateRequest(BaseModel):
    """Parsial per field; array dikirim utuh (menghapus item = kirim array tanpa item itu)."""

    tldr: Optional[str] = None
    decisions: Optional[list[str]] = None
    topics: Optional[list[str]] = None

    @field_validator("tldr")
    @classmethod
    def _tldr_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Ringkasan eksekutif tidak boleh kosong")
        return value

    @field_validator("decisions", "topics")
    @classmethod
    def _strip_items(cls, value: list[str] | None) -> list[str] | None:
        return _clean_items(value)


class SummaryResponse(BaseModel):
    id: uuid.UUID
    tldr: str
    decisions: list[str]
    topics: list[str]

    model_config = ConfigDict(from_attributes=True)


class SpeakerRenameRequest(BaseModel):
    renames: dict[str, str] = Field(min_length=1)

    @field_validator("renames")
    @classmethod
    def _names_valid(cls, value: dict[str, str]) -> dict[str, str]:
        cleaned = {label: name.strip() for label, name in value.items()}
        for name in cleaned.values():
            if not 1 <= len(name) <= 100:
                raise ValueError("Nama speaker harus 1-100 karakter")
        return cleaned


class TranscriptResponse(BaseModel):
    id: uuid.UUID
    segments: list[dict]

    model_config = ConfigDict(from_attributes=True)
