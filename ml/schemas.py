from pydantic import BaseModel
from typing import Optional


class TranscriptSegment(BaseModel):
    speaker: str
    start: float
    end: float
    text: str


class TranscriptResult(BaseModel):
    segments: list[TranscriptSegment]
    language: str
    duration: float


class SummaryResult(BaseModel):
    tldr: str
    decisions: list[str]
    topics: list[str]


class ActionItem(BaseModel):
    task: str
    assignee_name: Optional[str] = None
    due_date_text: Optional[str] = None
