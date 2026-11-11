from app.config import settings


def test_public_config_needs_no_auth_and_reflects_settings(client):
    response = client.get("/api/v1/config")

    assert response.status_code == 200
    body = response.json()
    assert body["allowed_audio_formats"] == settings.allowed_audio_formats_list
    assert body["avatar_max_size_mb"] == settings.AVATAR_MAX_SIZE_MB
    assert body["recording_poll_interval_seconds"] == settings.RECORDING_POLL_INTERVAL_SECONDS
    assert body["recording_poll_max_minutes"] == settings.RECORDING_POLL_MAX_MINUTES
    assert 0 < body["max_upload_size_mb"] <= settings.MAX_UPLOAD_SIZE_MB


def test_public_config_only_exposes_whitelisted_fields(client):
    # Endpoint ini tanpa auth: kalau ada yang menambah field baru ke response,
    # tes ini memaksa dia sadar dan memperbarui daftar ini dengan sengaja.
    body = client.get("/api/v1/config").json()

    assert set(body) == {
        "max_upload_size_mb",
        "allowed_audio_formats",
        "avatar_max_size_mb",
        "recording_poll_interval_seconds",
        "recording_poll_max_minutes",
    }
