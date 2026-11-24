from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

from app.models.action_item import ActionItem, ActionItemSource
from app.models.meeting import NotulenStatus
from app.models.notulen_version import NotulenVersion, NotulenVersionKind
from app.services import notulen as notulen_service


def _summary(**overrides):
    return SimpleNamespace(
        **{"tldr": "Rapat anggaran", "decisions": ["Setuju"], "topics": ["Anggaran"], **overrides}
    )


def _ai_item(**overrides):
    return SimpleNamespace(
        **{
            "task": "Siapkan anggaran",
            "assignee_name": "Pak Budi",
            "due_date_text": "Jumat depan",
            **overrides,
        }
    )


def _run_save(db, meeting, items, summary=None):
    notulen_service.save_ai_results(
        db, meeting, list(meeting.participants), summary or _summary(), items
    )
    db.commit()
    db.refresh(meeting)


def test_save_ai_results_creates_draft_and_ai_snapshot(db_session, make_user, make_meeting):
    meeting = make_meeting(make_user(), [make_user()])

    _run_save(db_session, meeting, [_ai_item()])

    assert meeting.notulen_status == NotulenStatus.draft
    versions = db_session.query(NotulenVersion).filter_by(meeting_id=meeting.id).all()
    assert len(versions) == 1
    assert versions[0].kind == NotulenVersionKind.ai
    assert versions[0].version is None
    assert versions[0].content["action_items"][0] == {
        "task": "Siapkan anggaran",
        "assignee_name": "Pak Budi",
        "due_date_text": "Jumat depan",
    }


def test_unmatched_ai_values_are_kept_for_review(db_session, make_user, make_meeting):
    meeting = make_meeting(make_user(), [make_user()])

    _run_save(db_session, meeting, [_ai_item()])

    item = db_session.query(ActionItem).filter_by(meeting_id=meeting.id).one()
    assert item.assignee_participant_id is None
    assert item.due_date is None
    assert item.ai_assignee_text == "Pak Budi"
    assert item.ai_due_date_text == "Jumat depan"
    assert notulen_service.needs_review(item) is True


def test_matched_ai_values_leave_no_review_flag(db_session, make_user, make_meeting):
    member = make_user()
    member.name = "Budi Santoso"
    db_session.commit()
    meeting = make_meeting(make_user(), [member])

    _run_save(
        db_session,
        meeting,
        [_ai_item(assignee_name="Budi Santoso", due_date_text="2026-12-01")],
    )

    item = db_session.query(ActionItem).filter_by(meeting_id=meeting.id).one()
    assert item.assignee_participant_id is not None
    assert item.due_date == date(2026, 12, 1)
    assert item.ai_assignee_text is None
    assert item.ai_due_date_text is None
    assert notulen_service.needs_review(item) is False


def test_save_ai_results_keeps_manual_action_items(db_session, make_user, make_meeting):
    meeting = make_meeting(make_user(), [make_user()])
    db_session.add(
        ActionItem(meeting_id=meeting.id, task="Tugas manual", source=ActionItemSource.manual)
    )
    db_session.commit()

    _run_save(db_session, meeting, [_ai_item()])

    tasks = {i.task for i in db_session.query(ActionItem).filter_by(meeting_id=meeting.id)}
    assert tasks == {"Tugas manual", "Siapkan anggaran"}


def test_has_unsent_changes_only_after_edit_post_publish(db_session, make_user, make_meeting):
    meeting = make_meeting(make_user(), [make_user()], notulen_status=NotulenStatus.published)
    t0 = datetime.now(timezone.utc)
    db_session.add(
        NotulenVersion(
            meeting_id=meeting.id,
            kind=NotulenVersionKind.published,
            version=1,
            content={},
            created_at=t0,
        )
    )
    db_session.commit()
    db_session.refresh(meeting)

    assert notulen_service.build_notulen_meta(meeting).has_unsent_changes is False

    meeting.notulen_edited_at = t0 + timedelta(minutes=1)
    db_session.commit()
    meta = notulen_service.build_notulen_meta(meeting)
    assert meta.has_unsent_changes is True
    assert meta.current_version == 1

    meeting.notulen_status = NotulenStatus.draft
    db_session.commit()
    assert notulen_service.build_notulen_meta(meeting).has_unsent_changes is False


def test_is_notulen_visible(db_session, make_user, make_meeting):
    organizer, member = make_user(), make_user()
    meeting = make_meeting(organizer, [member], notulen_status=NotulenStatus.draft)

    assert notulen_service.is_notulen_visible(meeting, organizer.id) is True
    assert notulen_service.is_notulen_visible(meeting, member.id) is False
    assert notulen_service.is_notulen_visible(meeting, None) is False

    meeting.notulen_status = NotulenStatus.published
    db_session.commit()
    assert notulen_service.is_notulen_visible(meeting, member.id) is True
