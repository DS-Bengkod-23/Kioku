import io

from PIL import Image

from app.services import storage


def _make_image_bytes(fmt: str) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (2, 2), color="red").save(buf, format=fmt)
    return buf.getvalue()


def _mock_storage(monkeypatch):
    monkeypatch.setattr(storage, "upload_avatar_file", lambda file_bytes, filename, user_id: "avatars/fake-key.png")
    monkeypatch.setattr(storage, "get_avatar_url", lambda object_key: f"http://localhost:9000/bucket/{object_key}")
    monkeypatch.setattr(storage, "delete_file", lambda object_key: None)


def test_upload_avatar_sets_avatar_url(client, make_user, auth_headers, monkeypatch):
    _mock_storage(monkeypatch)
    user = make_user()

    response = client.post(
        "/api/v1/auth/me/avatar",
        headers=auth_headers(user),
        files={"file": ("avatar.png", _make_image_bytes("PNG"), "image/png")},
    )

    assert response.status_code == 200
    assert response.json()["avatar_url"] == "http://localhost:9000/bucket/avatars/fake-key.png"


def test_upload_avatar_rejects_unsupported_extension(client, make_user, auth_headers):
    user = make_user()

    response = client.post(
        "/api/v1/auth/me/avatar",
        headers=auth_headers(user),
        files={"file": ("notes.txt", b"hello world", "text/plain")},
    )

    assert response.status_code == 400


def test_upload_avatar_rejects_content_mismatched_extension(client, make_user, auth_headers):
    user = make_user()

    # Isinya JPEG asli tapi diklaim .png -- harus ditolak walau ekstensinya valid.
    response = client.post(
        "/api/v1/auth/me/avatar",
        headers=auth_headers(user),
        files={"file": ("avatar.png", _make_image_bytes("JPEG"), "image/png")},
    )

    assert response.status_code == 400


def test_upload_avatar_rejects_oversized_file(client, make_user, auth_headers, monkeypatch):
    monkeypatch.setattr("app.services.auth._MAX_AVATAR_SIZE_MB", 0)
    user = make_user()

    response = client.post(
        "/api/v1/auth/me/avatar",
        headers=auth_headers(user),
        files={"file": ("avatar.png", _make_image_bytes("PNG"), "image/png")},
    )

    assert response.status_code == 400


def test_upload_avatar_replaces_old_object(client, db_session, make_user, auth_headers, monkeypatch):
    deleted_keys = []
    monkeypatch.setattr(storage, "upload_avatar_file", lambda file_bytes, filename, user_id: "avatars/second-key.png")
    monkeypatch.setattr(storage, "get_avatar_url", lambda object_key: f"http://localhost:9000/bucket/{object_key}")
    monkeypatch.setattr(storage, "delete_file", lambda object_key: deleted_keys.append(object_key))

    user = make_user()
    user.avatar_object_key = "avatars/first-key.png"
    db_session.commit()

    response = client.post(
        "/api/v1/auth/me/avatar",
        headers=auth_headers(user),
        files={"file": ("avatar.png", _make_image_bytes("PNG"), "image/png")},
    )

    assert response.status_code == 200
    assert response.json()["avatar_url"] == "http://localhost:9000/bucket/avatars/second-key.png"
    assert deleted_keys == ["avatars/first-key.png"]


def test_delete_avatar_clears_avatar_url(client, make_user, auth_headers, monkeypatch):
    _mock_storage(monkeypatch)
    user = make_user()
    client.post(
        "/api/v1/auth/me/avatar",
        headers=auth_headers(user),
        files={"file": ("avatar.png", _make_image_bytes("PNG"), "image/png")},
    )

    response = client.delete("/api/v1/auth/me/avatar", headers=auth_headers(user))

    assert response.status_code == 200
    assert response.json()["avatar_url"] is None


def test_get_me_exposes_null_avatar_url_by_default(client, make_user, auth_headers):
    user = make_user()

    response = client.get("/api/v1/auth/me", headers=auth_headers(user))

    assert response.status_code == 200
    assert response.json()["avatar_url"] is None
