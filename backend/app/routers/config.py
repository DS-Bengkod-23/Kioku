from fastapi import APIRouter

from app.config import settings
from app.schemas.config import PublicConfigResponse

router = APIRouter(tags=["config"])


@router.get("/config", response_model=PublicConfigResponse)
def get_public_config():
    return PublicConfigResponse(
        # Batas khusus provider (mis. 25MB OpenAI) tetap divalidasi backend saat
        # upload (services/recording.py) dengan pesan yang lebih spesifik.
        max_upload_size_mb=settings.MAX_UPLOAD_SIZE_MB,
        allowed_audio_formats=settings.allowed_audio_formats_list,
        avatar_max_size_mb=settings.AVATAR_MAX_SIZE_MB,
        recording_poll_interval_seconds=settings.RECORDING_POLL_INTERVAL_SECONDS,
        recording_poll_max_minutes=settings.RECORDING_POLL_MAX_MINUTES,
    )
