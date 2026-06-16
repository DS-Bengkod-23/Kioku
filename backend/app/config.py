from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# .env lives at the repo root, two levels up from this file (app/config.py → app/ → backend/ → root)
_ROOT_ENV = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ROOT_ENV),
        env_file_encoding="utf-8",
        case_sensitive=False,
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

    # LLM Provider
    LLM_PROVIDER: str = "openai"

    # Ollama
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:7b"

    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    # Hugging Face
    HF_TOKEN: str = ""

    # Whisper
    WHISPER_MODEL: str = "large-v3"

    # File upload
    MAX_UPLOAD_SIZE_MB: int = 200
    MAX_AUDIO_DURATION_HOURS: int = 2
    ALLOWED_AUDIO_FORMATS: str = "mp3,mp4,wav,m4a"

    # App
    APP_ENV: str = "development"
    APP_BASE_URL: str = "http://localhost:3000"
    BACKEND_BASE_URL: str = "http://localhost:8000"
    CORS_ORIGINS: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    @property
    def allowed_audio_formats_list(self) -> list[str]:
        return [fmt.strip() for fmt in self.ALLOWED_AUDIO_FORMATS.split(",")]


settings = Settings()
