from app.models.meeting import NotulenStatus


def _setup(make_user, make_meeting, **kwargs):
    organizer, member = make_user(), make_user()
    meeting = make_meeting(
        organizer, [member], with_notulen=True, notulen_status=kwargs.pop("status", NotulenStatus.draft), **kwargs
    )
    return organizer, member, meeting


def test_member_gets_no_notulen_content_while_draft(client, make_user, make_meeting, auth_headers):
    _, member, meeting = _setup(make_user, make_meeting)

    body = client.get(f"/api/v1/meetings/{meeting.id}", headers=auth_headers(member)).json()

    assert body["summary"] is None
    assert body["transcript"] is None
    assert body["action_items"] == []
    assert body["notulen"]["status"] == "draft"
    assert body["notulen"]["needs_review_count"] == 0


def test_organizer_sees_draft_with_review_fields(client, make_user, make_meeting, auth_headers):
    organizer, _, meeting = _setup(make_user, make_meeting)

    body = client.get(f"/api/v1/meetings/{meeting.id}", headers=auth_headers(organizer)).json()

    assert body["summary"]["tldr"] == "Ringkasan AI"
    item = body["action_items"][0]
    assert {"needs_review", "ai_assignee_text", "ai_due_date_text"} <= item.keys()
    assert item["needs_review"] is False


def test_member_sees_notulen_after_publish(client, make_user, make_meeting, auth_headers):
    _, member, meeting = _setup(make_user, make_meeting, status=NotulenStatus.published)

    body = client.get(f"/api/v1/meetings/{meeting.id}", headers=auth_headers(member)).json()

    assert body["summary"] is not None
    assert len(body["action_items"]) == 1


def test_rsvp_response_hides_draft(client, make_user, make_meeting, auth_headers):
    _, member, meeting = _setup(make_user, make_meeting)

    response = client.patch(
        f"/api/v1/meetings/{meeting.id}/rsvp",
        json={"response": "akan_hadir"},
        headers=auth_headers(member),
    )

    assert response.status_code == 200
    assert response.json()["summary"] is None
    assert response.json()["action_items"] == []


def test_member_pdf_404_while_draft(client, make_user, make_meeting, auth_headers):
    _, member, meeting = _setup(make_user, make_meeting)

    response = client.get(f"/api/v1/meetings/{meeting.id}/notulen.pdf", headers=auth_headers(member))

    assert response.status_code == 404
    assert response.json()["detail"] == "Notulen belum tersedia"


def test_organizer_can_download_draft_pdf(client, make_user, make_meeting, auth_headers):
    organizer, _, meeting = _setup(make_user, make_meeting)

    response = client.get(f"/api/v1/meetings/{meeting.id}/notulen.pdf", headers=auth_headers(organizer))

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"


def test_search_ignores_draft_content_for_member(client, make_user, make_meeting, auth_headers):
    organizer, member, _ = _setup(make_user, make_meeting)

    as_member = client.get("/api/v1/meetings/search?q=Ringkasan", headers=auth_headers(member)).json()
    as_organizer = client.get("/api/v1/meetings/search?q=Ringkasan", headers=auth_headers(organizer)).json()

    assert as_member["total"] == 0
    assert as_organizer["total"] == 1


def test_search_by_title_still_works_for_member_while_draft(client, make_user, make_meeting, auth_headers):
    _, member, _ = _setup(make_user, make_meeting)

    body = client.get("/api/v1/meetings/search?q=Team Sync", headers=auth_headers(member)).json()

    assert body["total"] == 1


def test_list_item_exposes_notulen_status(client, make_user, make_meeting, auth_headers):
    _, member, _ = _setup(make_user, make_meeting)

    body = client.get("/api/v1/meetings/", headers=auth_headers(member)).json()

    assert body["items"][0]["notulen_status"] == "draft"
