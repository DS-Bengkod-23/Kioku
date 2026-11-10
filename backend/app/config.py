from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# .env lives at the repo root, two levels up from this file (app/config.py → app/ → backend/ → root)
_ROOT_ENV = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ROOT_ENV),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    DATABASE_URL: str

    # Redis
    REDIS_URL: str

    # MinIO
    MINIO_ENDPOINT: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_BUCKET: str
    MINIO_SECURE: bool = False
    # Host:port yang bisa diakses langsung dari browser user (beda dari
    # MINIO_ENDPOINT yang dipakai backend-api/celery-worker di dalam network
    # Docker, mis. "minio:9000") -- dipakai buat bikin avatar_url yang
    # ditaruh langsung di <img src> tanpa lewat proxy backend. Kosong berarti
    # sama dengan MINIO_ENDPOINT (berlaku di prod: R2 endpoint sudah publik).
    MINIO_PUBLIC_ENDPOINT: str = ""

    # Email
    SMTP_HOST: str
    SMTP_PORT: int
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_USE_TLS: bool = False

    # Auth
    JWT_SECRET_KEY: str
    JWT_EXPIRE_MINUTES: int = 1440
    CHECKIN_TOKEN_EXPIRE_HOURS: int = 24

    # Akun admin/superadmin yang dibuat otomatis saat backend-api start.
    # Kosong = dilewati. Lihat services/seed.py untuk aturan idempotensinya.
    SUPERADMIN_EMAIL: str = ""
    SUPERADMIN_PASSWORD: str = ""
    ADMIN_EMAIL: str = ""
    ADMIN_PASSWORD: str = ""

    # Google SSO
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_SSO_ENABLED: bool = True

    # Google Calendar sync
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_CALENDAR_REDIRECT_URI: str = ""
    GOOGLE_TOKEN_ENCRYPTION_KEY: str = ""
    GOOGLE_CALENDAR_SYNC_ENABLED: bool = True

    # Provider LLM aktif untuk transcribe + summary/action item extraction.
    # Pilihan: 'openai' atau 'gemini'. Ganti nilai ini di .env lalu rebuild+restart
    # celery-worker untuk pindah provider tanpa ubah kode.
    LLM_PROVIDER: str = "gemini"

    # Gemini (dipakai untuk transcribe, summary, dan action item extraction kalau LLM_PROVIDER=gemini)
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.1-flash-lite"

    # OpenAI (dipakai untuk transcribe, summary, dan action item extraction kalau LLM_PROVIDER=openai)
    OPENAI_API_KEY: str = ""
    OPENAI_TRANSCRIBE_MODEL: str = "whisper-1"
    OPENAI_MODEL: str = "gpt-4o-mini"

    # Hugging Face
    HF_TOKEN: str = ""

    # Timeout panggilan ke OpenAI/Gemini (detik). Transcribe lebih longgar karena
    # request-nya membawa file audio; extract cuma teks.
    LLM_TRANSCRIBE_TIMEOUT_SECONDS: int = 300
    LLM_EXTRACT_TIMEOUT_SECONDS: int = 120

    # Celery pipeline pemrosesan rekaman. Batas waktu sengaja longgar supaya audio
    # 2 jam yang sah tidak terbunuh: soft limit bisa ditangkap untuk cleanup, hard
    # limit membunuh task.
    PIPELINE_MAX_RETRIES: int = 3
    PIPELINE_RETRY_BACKOFF_SECONDS: int = 60
    PIPELINE_RETRY_BACKOFF_MAX_SECONDS: int = 600
    PIPELINE_SOFT_TIME_LIMIT_SECONDS: int = 10800
    PIPELINE_TIME_LIMIT_SECONDS: int = 12600

    # File upload
    MAX_UPLOAD_SIZE_MB: int = 200
    MAX_AUDIO_DURATION_HOURS: int = 2
    ALLOWED_AUDIO_FORMATS: str = "mp3,mp4,wav,m4a"
    # Hard-cap endpoint transkripsi OpenAI (berlaku endpoint-wide, bukan per-model).
    # Hanya dipakai kalau LLM_PROVIDER=openai; ubah kalau OpenAI mengubah batasnya.
    OPENAI_TRANSCRIBE_MAX_UPLOAD_MB: int = 25
    AVATAR_MAX_SIZE_MB: int = 5

    # Google Calendar sync (timeout HTTP dan retry task Celery-nya)
    CALENDAR_API_TIMEOUT_SECONDS: int = 10
    CALENDAR_SYNC_MAX_RETRIES: int = 3
    CALENDAR_SYNC_RETRY_BACKOFF_SECONDS: int = 30
    CALENDAR_SYNC_RETRY_BACKOFF_MAX_SECONDS: int = 300

    # Polling status rekaman di frontend (dikirim lewat GET /config)
    RECORDING_POLL_INTERVAL_SECONDS: int = 3
    RECORDING_POLL_MAX_MINUTES: int = 60

    # App
    APP_ENV: str = "development"
    APP_BASE_URL: str = "http://localhost:3000"
    BACKEND_BASE_URL: str = "http://localhost:8000"
    CORS_ORIGINS: str = "http://localhost:3000"

    # Branding (notulen PDF header)
    ORG_NAME: str = "UNIVERSITAS DIAN NUSWANTORO"
    ORG_LOGO_PATH: str = "assets/logo.png"

    @property
    def minio_public_endpoint(self) -> str:
        return self.MINIO_PUBLIC_ENDPOINT or self.MINIO_ENDPOINT

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    @property
    def allowed_audio_formats_list(self) -> list[str]:
        return [fmt.strip() for fmt in self.ALLOWED_AUDIO_FORMATS.split(",")]

    @property
    def max_audio_duration_seconds(self) -> float:
        return self.MAX_AUDIO_DURATION_HOURS * 3600


settings = Settings()
