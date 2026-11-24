from pydantic import BaseModel, ConfigDict, field_validator, model_validator
from typing import Optional, Any
from datetime import date
from uuid import UUID
import enum

class ActionItemStatus(str, enum.Enum):
    open = "open"
    done = "done"

class AssigneeResponse(BaseModel):
    id: UUID
    name: str
    email: str

    model_config = ConfigDict(from_attributes=True)

class ActionItemResponse(BaseModel):
    id: UUID
    task: str
    assignee_participant_id: Optional[UUID] = None
    assignee: Optional[AssigneeResponse] = None
    due_date: Optional[date] = None
    status: ActionItemStatus
    ai_assignee_text: Optional[str] = None
    ai_due_date_text: Optional[str] = None
    needs_review: bool = False

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode='before')
    @classmethod
    def extract_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            return data
            
        assignee = None
        if hasattr(data, 'assignee_participant') and data.assignee_participant and hasattr(data.assignee_participant, 'user') and data.assignee_participant.user:
            assignee = AssigneeResponse(
                id=data.assignee_participant.user.id,
                name=data.assignee_participant.user.name,
                email=data.assignee_participant.user.email
            )
            
        status = data.status.value if hasattr(data.status, 'value') else data.status

        return {
            "id": data.id,
            "task": data.task,
            "assignee_participant_id": data.assignee_participant_id,
            "assignee": assignee,
            "due_date": data.due_date,
            "status": status,
            "ai_assignee_text": data.ai_assignee_text,
            "ai_due_date_text": data.ai_due_date_text,
            "needs_review": data.ai_assignee_text is not None or data.ai_due_date_text is not None,
        }

def _strip_task(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    value = value.strip()
    if not value:
        raise ValueError("Teks tugas tidak boleh kosong")
    return value

class ActionItemUpdateRequest(BaseModel):
    status: Optional[ActionItemStatus] = None
    assignee_participant_id: Optional[UUID] = None
    due_date: Optional[date] = None
    task: Optional[str] = None  # organizer saja
    dismiss_review: Optional[bool] = None  # organizer saja: hapus penanda "Perlu dicek"

    _clean_task = field_validator("task")(_strip_task)

class ActionItemCreateRequest(BaseModel):
    task: str
    assignee_participant_id: Optional[UUID] = None
    due_date: Optional[date] = None

class MeetingSimpleResponse(BaseModel):
    id: UUID
    title: str
    scheduled_at: Any  # datetime

    model_config = ConfigDict(from_attributes=True)

class MyActionItemResponse(BaseModel):
    id: UUID
    task: str
    due_date: Optional[date] = None
    status: ActionItemStatus
    meeting: MeetingSimpleResponse

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode='before')
    @classmethod
    def extract_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            return data
            
        status = data.status.value if hasattr(data.status, 'value') else data.status

        return {
            "id": data.id,
            "task": data.task,
            "due_date": data.due_date,
            "status": status,
            "meeting": data.meeting,
        }

class MyActionItemListResponse(BaseModel):
    items: list[MyActionItemResponse]
