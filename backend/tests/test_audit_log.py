import uuid

from app.models.audit_log import AuditAction, AuditLog
from app.models.user import User


def test_audit_log_round_trip(db_session):
    actor = User(email="actor@example.com", name="Actor", password_hash="hashed")
    db_session.add(actor)
    db_session.commit()
    db_session.refresh(actor)

    target_id = uuid.uuid4()
    log = AuditLog(
        actor_id=actor.id,
        action=AuditAction.suspend_user,
        target_type="user",
        target_id=target_id,
        reason="abuse report",
    )
    db_session.add(log)
    db_session.commit()
    db_session.refresh(log)

    fetched = db_session.query(AuditLog).filter(AuditLog.id == log.id).one()
    assert fetched.actor_id == actor.id
    assert fetched.action == AuditAction.suspend_user
    assert fetched.target_type == "user"
    assert fetched.target_id == target_id
    assert fetched.reason == "abuse report"
    assert fetched.created_at is not None
