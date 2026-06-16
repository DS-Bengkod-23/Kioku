import uuid
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.action_item import ActionItem, ActionItemStatus
from app.models.meeting import Meeting
from app.models.participant import MeetingParticipant
from app.schemas.action_item import ActionItemUpdateRequest

def update_action_item(db: Session, action_item_id: uuid.UUID, user_id: uuid.UUID, data: ActionItemUpdateRequest) -> ActionItem:
    action_item = db.query(ActionItem).filter(ActionItem.id == action_item_id).first()
    if not action_item:
        raise HTTPException(status_code=404, detail="Action item not found")

    meeting = db.query(Meeting).filter(Meeting.id == action_item.meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if meeting.organizer_id == user_id:
        pass
    else:
        if action_item.assignee_participant and action_item.assignee_participant.user_id == user_id:
            pass
        else:
            raise HTTPException(status_code=403, detail="Not authorized to update this action item")

    action_item.status = data.status
    db.commit()
    db.refresh(action_item)
    return action_item

def get_my_action_items(db: Session, user_id: uuid.UUID, status_filter: Optional[ActionItemStatus] = None) -> list[ActionItem]:
    query = db.query(ActionItem).join(
        MeetingParticipant, ActionItem.assignee_participant_id == MeetingParticipant.id
    ).filter(
        MeetingParticipant.user_id == user_id
    )

    if status_filter:
        query = query.filter(ActionItem.status == status_filter)

    return query.all()
