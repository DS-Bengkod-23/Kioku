from pydantic import BaseModel


class PublicConfigResponse(BaseModel):
    """Setting yang aman dilihat siapa pun (endpoint ini tanpa auth) dan dibutuhkan
    frontend supaya tidak menulis ulang angka dari .env. JANGAN tambahkan field
    rahasia (API key, secret, URL internal) ke sini."""

    max_upload_size_mb: int
    allowed_audio_formats: list[str]
    avatar_max_size_mb: int
    recording_poll_interval_seconds: int
    recording_poll_max_minutes: int
