from pydantic import BaseModel, ConfigDict, model_validator
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
    assignee: Optional[AssigneeResponse] = None
    due_date: Optional[date] = None
    status: ActionItemStatus

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
            "assignee": assignee,
            "due_date": data.due_date,
            "status": status,
        }

class ActionItemUpdateRequest(BaseModel):
    status: Optional[ActionItemStatus] = None
    assignee_participant_id: Optional[UUID] = None

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
