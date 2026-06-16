import secrets
import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.models.invitation import Invitation

def generate_invitation_token() -> str:
    return secrets.token_urlsafe(32)

def create_invitations(db: Session, meeting_id: uuid.UUID, participant_ids: list[str | uuid.UUID], expire_hours: int):
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=expire_hours)
    
    invitations = []
    for p_id in participant_ids:
        invitation = Invitation(
            participant_id=p_id,
            token=generate_invitation_token(),
            expires_at=expires_at
        )
        db.add(invitation)
        invitations.append(invitation)
        
    db.commit()
    return invitations
