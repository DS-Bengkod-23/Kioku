import pytest

from app.models.action_item import ActionItem
from app.models.meeting import Meeting, NotulenStatus
from app.models.transcript import Transcript

ORGANIZER_ONLY = "Hanya organizer yang bisa mengedit notulen"


@pytest.fixture
def ctx(db_session, make_user, make_meeting, auth_headers):
    organizer, member = make_user(), make_user()
    meeting = make_meeting(
        organizer, [member], with_notulen=True, notulen_status=NotulenStatus.published
    )
    item = db_session.query(ActionItem).filter_by(meeting_id=meeting.id).one()

    class Ctx:
        pass

    c = Ctx()
    c.db, c.organizer, c.member, c.meeting, c.item = db_session, organizer, member, meeting, item
    c.org_h, c.mem_h = auth_headers(organizer), auth_headers(member)
    c.meeting_id, c.item_id = meeting.id, item.id
    return c


def _fresh(ctx):
    ctx.db.expire_all()
    return ctx.db.get(Meeting, ctx.meeting_id)


def test_update_summary_partial_and_strips_blank_items(client, ctx):
    response = client.patch(
        f"/api/v1/meetings/{ctx.meeting_id}/summary",
        json={"decisions": ["  Keputusan B ", "", "   "]},
        headers=ctx.org_h,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["decisions"] == ["Keputusan B"]
    assert body["tldr"] == "Ringkasan AI"
    assert body["topics"] == ["Topik A"]
    assert _fresh(ctx).notulen_edited_at is not None


def test_update_summary_rejects_blank_tldr(client, ctx):
    response = client.patch(
        f"/api/v1/meetings/{ctx.meeting_id}/summary", json={"tldr": "   "}, headers=ctx.org_h
    )

    assert response.status_code == 422
    assert _fresh(ctx).summary.tldr == "Ringkasan AI"


def test_member_cannot_edit_summary(client, ctx):
    response = client.patch(
        f"/api/v1/meetings/{ctx.meeting_id}/summary", json={"tldr": "Hack"}, headers=ctx.mem_h
    )

    assert response.status_code == 403
    assert response.json()["detail"] == ORGANIZER_ONLY


def test_update_summary_404_before_ai_finished(client, db_session, make_user, make_meeting, auth_headers):
    organizer = make_user()
    meeting = make_meeting(organizer)

    response = client.patch(
        f"/api/v1/meetings/{meeting.id}/summary", json={"tldr": "x"}, headers=auth_headers(organizer)
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Notulen belum tersedia"


def test_rename_speakers_updates_all_segments(client, ctx):
    response = client.patch(
        f"/api/v1/meetings/{ctx.meeting_id}/transcript/speakers",
        json={"renames": {"SPEAKER_00": "Budi"}},
        headers=ctx.org_h,
    )

    assert response.status_code == 200
    assert {s["speaker"] for s in response.json()["segments"]} == {"Budi"}
    meeting = _fresh(ctx)
    assert {s["speaker"] for s in meeting.transcript.segments} == {"Budi"}
    assert meeting.notulen_edited_at is None


def test_rename_unknown_speaker_400_and_transcript_unchanged(client, ctx):
    response = client.patch(
        f"/api/v1/meetings/{ctx.meeting_id}/transcript/speakers",
        json={"renames": {"SPEAKER_00": "Budi", "SPEAKER_09": "Ani"}},
        headers=ctx.org_h,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Speaker 'SPEAKER_09' tidak ada di transkrip"
    transcript = ctx.db.query(Transcript).filter_by(meeting_id=ctx.meeting_id).one()
    ctx.db.refresh(transcript)
    assert {s["speaker"] for s in transcript.segments} == {"SPEAKER_00"}


@pytest.mark.parametrize("bad_name", ["  ", "x" * 101])
def test_rename_invalid_target_422(client, ctx, bad_name):
    response = client.patch(
        f"/api/v1/meetings/{ctx.meeting_id}/transcript/speakers",
        json={"renames": {"SPEAKER_00": bad_name}},
        headers=ctx.org_h,
    )

    assert response.status_code == 422


def test_rename_empty_map_422(client, ctx):
    response = client.patch(
        f"/api/v1/meetings/{ctx.meeting_id}/transcript/speakers",
        json={"renames": {}},
        headers=ctx.org_h,
    )

    assert response.status_code == 422


def test_member_cannot_rename_speakers(client, ctx):
    response = client.patch(
        f"/api/v1/meetings/{ctx.meeting_id}/transcript/speakers",
        json={"renames": {"SPEAKER_00": "Budi"}},
        headers=ctx.mem_h,
    )

    assert response.status_code == 403


def test_organizer_edits_task_member_cannot(client, ctx):
    as_member = client.patch(
        f"/api/v1/action-items/{ctx.item_id}", json={"task": "Hack"}, headers=ctx.mem_h
    )
    assert as_member.status_code == 403
    assert as_member.json()["detail"] == ORGANIZER_ONLY

    as_organizer = client.patch(
        f"/api/v1/action-items/{ctx.item_id}", json={"task": " Tugas baru "}, headers=ctx.org_h
    )
    assert as_organizer.status_code == 200
    assert as_organizer.json()["task"] == "Tugas baru"
    assert _fresh(ctx).notulen_edited_at is not None


def test_blank_task_rejected(client, ctx):
    response = client.patch(
        f"/api/v1/action-items/{ctx.item_id}", json={"task": "  "}, headers=ctx.org_h
    )

    assert response.status_code == 422


def _flag_item(ctx):
    ctx.item.ai_assignee_text = "Pak Budi"
    ctx.item.ai_due_date_text = "Jumat depan"
    ctx.item.assignee_participant_id = None
    ctx.db.commit()


def test_setting_assignee_clears_ai_assignee_text(client, ctx):
    _flag_item(ctx)
    participant_id = next(p.id for p in ctx.meeting.participants if p.user_id == ctx.member.id)

    body = client.patch(
        f"/api/v1/action-items/{ctx.item_id}",
        json={"assignee_participant_id": str(participant_id)},
        headers=ctx.org_h,
    ).json()

    assert body["ai_assignee_text"] is None
    assert body["ai_due_date_text"] == "Jumat depan"
    assert body["needs_review"] is True


def test_setting_due_date_clears_ai_due_date_text(client, ctx):
    _flag_item(ctx)

    body = client.patch(
        f"/api/v1/action-items/{ctx.item_id}", json={"due_date": "2026-12-01"}, headers=ctx.org_h
    ).json()

    assert body["ai_due_date_text"] is None
    assert body["ai_assignee_text"] == "Pak Budi"


def test_dismiss_review_clears_both_flags(client, ctx):
    _flag_item(ctx)

    body = client.patch(
        f"/api/v1/action-items/{ctx.item_id}", json={"dismiss_review": True}, headers=ctx.org_h
    ).json()

    assert body["ai_assignee_text"] is None
    assert body["ai_due_date_text"] is None
    assert body["needs_review"] is False
    assert _fresh(ctx).notulen_edited_at is not None


def test_member_cannot_dismiss_review(client, ctx):
    _flag_item(ctx)

    response = client.patch(
        f"/api/v1/action-items/{ctx.item_id}", json={"dismiss_review": True}, headers=ctx.mem_h
    )

    assert response.status_code == 403


def test_delete_action_item_organizer_only(client, ctx):
    assert client.delete(f"/api/v1/action-items/{ctx.item_id}", headers=ctx.mem_h).status_code == 403

    response = client.delete(f"/api/v1/action-items/{ctx.item_id}", headers=ctx.org_h)

    assert response.status_code == 204
    assert ctx.db.query(ActionItem).filter_by(id=ctx.item_id).count() == 0
    assert _fresh(ctx).notulen_edited_at is not None


def test_delete_missing_action_item_404(client, ctx):
    response = client.delete(
        "/api/v1/action-items/00000000-0000-0000-0000-000000000000", headers=ctx.org_h
    )

    assert response.status_code == 404


def test_create_action_item_marks_edited(client, ctx):
    response = client.post(
        f"/api/v1/meetings/{ctx.meeting_id}/action-items",
        json={"task": "Tugas manual"},
        headers=ctx.org_h,
    )

    assert response.status_code == 201
    assert _fresh(ctx).notulen_edited_at is not None


def test_status_toggle_does_not_mark_edited(client, ctx):
    response = client.patch(
        f"/api/v1/action-items/{ctx.item_id}", json={"status": "done"}, headers=ctx.mem_h
    )

    assert response.status_code == 200
    assert _fresh(ctx).notulen_edited_at is None
