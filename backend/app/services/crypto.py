from cryptography.fernet import Fernet
from app.config import settings


def _get_fernet() -> Fernet:
    if not settings.GOOGLE_TOKEN_ENCRYPTION_KEY:
        raise RuntimeError("GOOGLE_TOKEN_ENCRYPTION_KEY belum di-set di .env")
    return Fernet(settings.GOOGLE_TOKEN_ENCRYPTION_KEY.encode())


def encrypt_token(plain: str) -> str:
    return _get_fernet().encrypt(plain.encode()).decode()


def decrypt_token(cipher: str) -> str:
    return _get_fernet().decrypt(cipher.encode()).decode()
