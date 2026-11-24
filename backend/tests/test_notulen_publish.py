import email
from datetime import datetime, timezone

import pytest

from app.config import settings
from app.models.meeting import Meeting, NotulenStatus
from app.models.notulen_version import NotulenVersion, NotulenVersionKind
from app.services import email as email_service
from app.services import notulen as notulen_service
from app.tasks import send_notulen as send_notulen_module

ORGANIZER_ONLY = "Hanya organizer yang bisa mengedit notulen"


@pytest.fixture
def delays(monkeypatch):
    calls = []
    monkeypatch.setattr(
        send_notulen_module.send_notulen_task, "delay", lambda *args: calls.append(args)
    )
    return calls


@pytest.fixture
def ctx(db_session, make_user, make_meeting, auth_headers):
    organizer, member = make_user(), make_user()
    meeting = make_meeting(
        organizer, [member], with_notulen=True, notulen_status=NotulenStatus.draft
    )

    class Ctx:
        pass

    c = Ctx()
    c.db, c.organizer, c.member, c.meeting = db_session, organizer, member, meeting
    c.org_h, c.mem_h = auth_headers(organizer), auth_headers(member)
    c.id = meeting.id
    return c


def _publish(client, ctx):
    return client.post(f"/api/v1/meetings/{ctx.id}/notulen/publish", headers=ctx.org_h)


def _resend(client, ctx):
    return client.post(f"/api/v1/meetings/{ctx.id}/notulen/resend", headers=ctx.org_h)


def _edit(client, ctx):
    return client.patch(
        f"/api/v1/meetings/{ctx.id}/summary", json={"tldr": "Ringkasan baru"}, headers=ctx.org_h
    )


def test_publish_creates_v1_and_enqueues_email(client, ctx, delays):
    response = _publish(client, ctx)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "published"
    assert body["current_version"] == 1
    assert body["has_unsent_changes"] is False
    assert delays == [(str(ctx.id), 1)]

    version = ctx.db.query(NotulenVersion).filter_by(kind=NotulenVersionKind.published).one()
    assert version.version == 1
    assert version.created_by == ctx.organizer.id
    assert version.content["tldr"] == "Ringkasan AI"
    assert version.content["decisions"] == ["Keputusan A"]
    item = version.content["action_items"][0]
    assert item["task"] == "Kirim laporan"
    assert item["assignee_name"] == ctx.member.name
    assert item["due_date"] is None


def test_publish_twice_returns_409(client, ctx, delays):
    _publish(client, ctx)

    response = _publish(client, ctx)

    assert response.status_code == 409
    assert response.json()["detail"] == "Notulen sudah dipublikasikan"
    assert len(delays) == 1


def test_member_cannot_publish(client, ctx, delays):
    response = client.post(f"/api/v1/meetings/{ctx.id}/notulen/publish", headers=ctx.mem_h)

    assert response.status_code == 403
    assert response.json()["detail"] == ORGANIZER_ONLY
    assert delays == []


def test_publish_before_ai_finished_404(client, db_session, make_user, make_meeting, auth_headers, delays):
    organizer = make_user()
    meeting = make_meeting(organizer)

    response = client.post(
        f"/api/v1/meetings/{meeting.id}/notulen/publish", headers=auth_headers(organizer)
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Notulen belum tersedia"


def test_resend_while_draft_409(client, ctx, delays):
    response = _resend(client, ctx)

    assert response.status_code == 409
    assert response.json()["detail"] == "Notulen belum dipublikasikan"


def test_resend_without_changes_returns_409(client, ctx, delays):
    _publish(client, ctx)

    response = _resend(client, ctx)

    assert response.status_code == 409
    assert response.json()["detail"] == "Tidak ada perubahan sejak versi terakhir"


def test_resend_after_edit_creates_v2(client, ctx, delays):
    _publish(client, ctx)
    _edit(client, ctx)

    response = _resend(client, ctx)

    assert response.status_code == 200
    body = response.json()
    assert body["current_version"] == 2
    assert body["has_unsent_changes"] is False
    assert delays[-1] == (str(ctx.id), 2)


def test_double_resend_second_returns_409(client, ctx, delays):
    _publish(client, ctx)
    _edit(client, ctx)

    first = _resend(client, ctx)
    second = _resend(client, ctx)

    assert first.status_code == 200
    assert second.status_code == 409
    assert len(delays) == 2  # publish + satu resend
    versions = ctx.db.query(NotulenVersion).filter_by(kind=NotulenVersionKind.published).count()
    assert versions == 2


def test_publish_after_redraft_continues_numbering(client, ctx, delays):
    _publish(client, ctx)
    ctx.db.expire_all()  # sesi test masih menyimpan status lama dari sebelum publish
    meeting = ctx.db.get(Meeting, ctx.id)
    meeting.notulen_status = NotulenStatus.draft
    ctx.db.commit()

    response = _publish(client, ctx)

    assert response.status_code == 200
    assert response.json()["current_version"] == 2


def test_version_label(db_session, make_user, make_meeting):
    meeting = make_meeting(make_user(), with_notulen=True, notulen_status=NotulenStatus.draft)
    assert notulen_service.version_label(meeting) == "DRAFT — belum dipublikasikan"

    db_session.add(
        NotulenVersion(
            meeting_id=meeting.id,
            kind=NotulenVersionKind.published,
            version=2,
            content={},
            created_at=datetime(2026, 11, 1, tzinfo=timezone.utc),
        )
    )
    meeting.notulen_status = NotulenStatus.published
    db_session.commit()
    db_session.refresh(meeting)
    assert notulen_service.version_label(meeting) == "Versi 2"

    meeting.notulen_edited_at = datetime(2026, 11, 19, 10, 0, tzinfo=timezone.utc)
    db_session.commit()
    assert notulen_service.version_label(meeting) == "Versi 2 · diperbarui 19/11/2026"


def test_root_message_id_domain(monkeypatch, make_user, make_meeting):
    meeting = make_meeting(make_user())
    participant_id = meeting.participants[0].id

    monkeypatch.setattr(settings, "SMTP_USER", "notulen@kampus.ac.id")
    root = email_service.notulen_root_message_id(meeting.id, participant_id)
    assert root == f"<notulen-{meeting.id}-{participant_id}@kampus.ac.id>"

    monkeypatch.setattr(settings, "SMTP_USER", "")
    assert email_service.notulen_root_message_id(meeting.id, participant_id).endswith("@kioku.local>")


class _FakeSmtp:
    def __init__(self, sent):
        self.sent = sent

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def sendmail(self, sender, recipients, message):
        self.sent.append(message)


def test_send_task_threads_followup_versions(db_session, make_user, make_meeting, monkeypatch):
    organizer, member = make_user(), make_user()
    meeting = make_meeting(
        organizer, [member], with_notulen=True, notulen_status=NotulenStatus.published
    )
    for number in (1, 2):
        db_session.add(
            NotulenVersion(
                meeting_id=meeting.id,
                kind=NotulenVersionKind.published,
                version=number,
                content={},
            )
        )
    db_session.commit()
    sent: list[str] = []
    monkeypatch.setattr(email_service, "_smtp_connection", lambda: _FakeSmtp(sent))
    participant = next(p for p in meeting.participants if p.user_id == member.id)
    root = email_service.notulen_root_message_id(meeting.id, participant.id)

    send_notulen_module.send_notulen_task(str(meeting.id), 1)
    send_notulen_module.send_notulen_task(str(meeting.id), 2)

    assert len(sent) == 2
    v1, v2 = (email.message_from_string(raw) for raw in sent)
    assert v1["Message-ID"] == root
    assert v1["In-Reply-To"] is None
    assert v2["Message-ID"] != root
    assert v2["In-Reply-To"] == root
    assert v2["References"] == root
    assert v2["Subject"] == "Notulen Rapat: Team Sync"
    assert v1["Subject"] == "Notulen Rapat: Team Sync"
    marker = "<p><b>Versi 2</b> — versi ini menggantikan notulen sebelumnya.</p>"
    assert marker in v2.get_payload(0).get_payload(decode=True).decode()
    assert "menggantikan" not in v1.get_payload(0).get_payload(decode=True).decode()
