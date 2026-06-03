from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional
import uuid

from app.database import get_db
from app.services.auth import get_current_user
from app.models.user import User
from app.models.action_item import ActionItemStatus
from app.schemas.action_item import ActionItemResponse, ActionItemUpdateRequest, MyActionItemListResponse
from app.services import action_item as action_item_service

router = APIRouter(tags=["action_items"])

@router.patch("/action-items/{action_item_id}", response_model=ActionItemResponse)
def update_action_item(
    action_item_id: uuid.UUID,
    data: ActionItemUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return action_item_service.update_action_item(db, action_item_id=action_item_id, user_id=current_user.id, data=data)

@router.get("/me/action-items", response_model=MyActionItemListResponse)
def get_my_action_items(
    status: Optional[ActionItemStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    items = action_item_service.get_my_action_items(db, user_id=current_user.id, status_filter=status)
    return {"items": items}
