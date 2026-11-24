from datetime import datetime, timedelta, timezone

from app.models.action_item import ActionItem
from app.models.meeting import NotulenStatus
from app.tasks import action_item_reminders


def _setup(db_session, make_user, make_meeting, status=NotulenStatus.draft):
    organizer, member = make_user(), make_user()
    meeting = make_meeting(organizer, [member], with_notulen=True, notulen_status=status)
    item = db_session.query(ActionItem).filter_by(meeting_id=meeting.id).one()
    token = next(p for p in meeting.participants if p.user_id == member.id).invitation.token
    return organizer, member, meeting, item, token


def _publish(db_session, meeting):
    meeting.notulen_status = NotulenStatus.published
    db_session.commit()


def test_checkin_info_hides_draft(client, db_session, make_user, make_meeting):
    *_, token = _setup(db_session, make_user, make_meeting)

    body = client.get(f"/api/v1/check-in/{token}").json()

    assert body["summary"] is None
    assert body["action_items"] == []
    assert body["notulen"]["status"] == "draft"
    assert body["notulen"]["needs_review_count"] == 0


def test_checkin_info_shows_notulen_after_publish(client, db_session, make_user, make_meeting):
    _, _, meeting, _, token = _setup(db_session, make_user, make_meeting)
    _publish(db_session, meeting)

    body = client.get(f"/api/v1/check-in/{token}").json()

    assert body["summary"]["tldr"] == "Ringkasan AI"
    assert len(body["action_items"]) == 1
    assert body["notulen"]["status"] == "published"


def test_checkin_action_item_update_404_while_draft(client, db_session, make_user, make_meeting):
    *_, item, token = _setup(db_session, make_user, make_meeting)

    response = client.patch(
        f"/api/v1/check-in/{token}/action-items/{item.id}", json={"status": "done"}
    )

    assert response.status_code == 404
    db_session.refresh(item)
    assert item.status.value == "open"


def test_checkin_action_item_update_works_after_publish(client, db_session, make_user, make_meeting):
    _, _, meeting, item, token = _setup(db_session, make_user, make_meeting)
    _publish(db_session, meeting)

    response = client.patch(
        f"/api/v1/check-in/{token}/action-items/{item.id}", json={"status": "done"}
    )

    assert response.status_code == 200


def test_checkin_pdf_404_while_draft(client, db_session, make_user, make_meeting):
    *_, token = _setup(db_session, make_user, make_meeting)

    assert client.get(f"/api/v1/check-in/{token}/notulen.pdf").status_code == 404


def test_my_action_items_excludes_draft_meetings(
    client, db_session, make_user, make_meeting, auth_headers
):
    _, member, meeting, _, _ = _setup(db_session, make_user, make_meeting)

    draft = client.get("/api/v1/me/action-items", headers=auth_headers(member)).json()
    assert draft["items"] == []

    _publish(db_session, meeting)
    published = client.get("/api/v1/me/action-items", headers=auth_headers(member)).json()
    assert len(published["items"]) == 1


def test_assignee_cannot_patch_status_while_draft(
    client, db_session, make_user, make_meeting, auth_headers
):
    _, member, _, item, _ = _setup(db_session, make_user, make_meeting)

    response = client.patch(
        f"/api/v1/action-items/{item.id}", json={"status": "done"}, headers=auth_headers(member)
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Action item not found"
    db_session.refresh(item)
    assert item.status.value == "open"


def test_organizer_can_patch_status_while_draft(
    client, db_session, make_user, make_meeting, auth_headers
):
    organizer, _, _, item, _ = _setup(db_session, make_user, make_meeting)

    response = client.patch(
        f"/api/v1/action-items/{item.id}", json={"status": "done"}, headers=auth_headers(organizer)
    )

    assert response.status_code == 200


def test_reminder_skips_draft_meetings(db_session, make_user, make_meeting, monkeypatch):
    _, _, meeting, item, _ = _setup(db_session, make_user, make_meeting)
    item.due_date = (datetime.now(timezone.utc) + timedelta(days=1)).date()
    db_session.commit()
    sent = []
    monkeypatch.setattr(
        action_item_reminders, "send_action_item_reminder_email", lambda **kw: sent.append(kw)
    )

    action_item_reminders.send_action_item_reminders_task()
    assert sent == []

    _publish(db_session, meeting)
    action_item_reminders.send_action_item_reminders_task()
    assert len(sent) == 1
