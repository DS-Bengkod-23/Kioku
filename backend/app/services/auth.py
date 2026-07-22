import io
import uuid
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from passlib.context import CryptContext
from PIL import Image
from fastapi import Depends, HTTPException, Request, UploadFile, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests
from google.auth import exceptions as google_exceptions
from app.config import settings
from app.database import get_db
from app.models.user import User, AuthProvider, UserRole
from app.schemas.auth import UserProfileResponse, UserProfileUpdateRequest
from app.services import storage

# Ekstensi yang diterima buat avatar, dan format Pillow yang harus terdeteksi
# untuk masing-masing -- sama seperti mutagen di services/recording.py, ini
# memastikan isi file benar-benar gambar sesuai klaim ekstensinya, bukan cuma
# percaya nama file dari client.
_AVATAR_FORMAT_BY_EXT = {"jpg": "JPEG", "jpeg": "JPEG", "png": "PNG", "webp": "WEBP"}
_MAX_AVATAR_SIZE_MB = 5

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
_bearer = HTTPBearer()


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


def create_access_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS256")


def _decode_user_token(token: str, db: Session) -> User:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token tidak valid atau sudah expired",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"])
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise credentials_exc
        # sub yang bukan UUID valid akan bikin query di bawah lempar DataError
        # Postgres (500), bukan 401 — validasi dulu di sini.
        uuid.UUID(user_id)
    except (JWTError, ValueError):
        raise credentials_exc

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exc
    if user.suspended_at is not None:
        # Checked on every request (not just at login) so suspension takes
        # effect on the suspended user's very next call, regardless of how
        # long their existing JWT still has left.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Akun ini disuspend",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    return _decode_user_token(credentials.credentials, db)


def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in (UserRole.admin, UserRole.superadmin):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Akses admin diperlukan")
    return current_user


def get_current_superadmin_user(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.superadmin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Akses superadmin diperlukan")
    return current_user


def get_current_user_from_cookie(request: Request, db: Session) -> User:
    # Dipakai khusus untuk endpoint yang diakses lewat full-page browser
    # navigation (mis. GET /auth/google/calendar/connect via window.location.href),
    # bukan axios/fetch — browser tidak mengirim header Authorization pada
    # navigasi biasa, cuma cookie. lib/api.ts sudah mirror JWT ke cookie
    # `access_token` (awalnya buat middleware Next.js), jadi dipakai ulang di sini.
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Belum login")
    return _decode_user_token(token, db)


def create_calendar_state_token(user_id: uuid.UUID) -> str:
    payload = {
        "sub": str(user_id),
        "purpose": "calendar_connect",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS256")


def decode_calendar_state_token(token: str) -> uuid.UUID:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"])
        if payload.get("purpose") != "calendar_connect":
            raise ValueError("wrong token purpose")
        return uuid.UUID(payload["sub"])
    except (JWTError, ValueError, KeyError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="State tidak valid atau sudah expired") from e


def create_password_reset_token(user_id: uuid.UUID) -> str:
    payload = {
        "sub": str(user_id),
        "purpose": "password_reset",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS256")


def decode_password_reset_token(token: str) -> uuid.UUID:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"])
        if payload.get("purpose") != "password_reset":
            raise ValueError("wrong token purpose")
        return uuid.UUID(payload["sub"])
    except (JWTError, ValueError, KeyError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token reset tidak valid atau sudah expired",
        ) from e


def authenticate_google(db: Session, id_token_str: str) -> User:
    try:
        payload = google_id_token.verify_oauth2_token(
            id_token_str, google_requests.Request(), settings.GOOGLE_CLIENT_ID
        )
    except (ValueError, google_exceptions.GoogleAuthError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID token Google tidak valid atau sudah expired",
        )

    if not payload.get("email_verified"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email akun Google belum diverifikasi",
        )

    google_sub = payload["sub"]
    email = payload["email"]
    name = payload.get("name", email)

    user = db.query(User).filter(User.google_sub == google_sub).first()
    if user is None:
        # Auto-link ke akun password yang sudah ada dengan email sama —
        # email Google selalu terverifikasi, jadi email sama = orang sama.
        user = db.query(User).filter(User.email == email).first()
        if user is not None:
            user.google_sub = google_sub
        else:
            user = User(
                id=uuid.uuid4(),
                email=email,
                name=name,
                password_hash=None,
                auth_provider=AuthProvider.google,
                google_sub=google_sub,
            )
            db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_profile(db: Session, user: User, data: UserProfileUpdateRequest) -> User:
    update_data = data.model_dump(exclude_unset=True)
    if "email" in update_data and update_data["email"] != user.email:
        if db.query(User).filter(User.email == update_data["email"]).first():
            raise HTTPException(status_code=400, detail="Email sudah terdaftar")
    for field, value in update_data.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user


def build_profile_response(user: User) -> UserProfileResponse:
    avatar_url = storage.get_avatar_url(user.avatar_object_key) if user.avatar_object_key else None
    return UserProfileResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        job_title=user.job_title,
        department=user.department,
        bio=user.bio,
        avatar_url=avatar_url,
        created_at=user.created_at,
    )


async def upload_avatar(db: Session, user: User, file: UploadFile) -> User:
    ext = (file.filename or "").rsplit(".", 1)[-1].lower() if file.filename and "." in file.filename else ""
    if ext not in _AVATAR_FORMAT_BY_EXT:
        raise HTTPException(
            status_code=400,
            detail=f"Format file tidak didukung. Gunakan: {', '.join(_AVATAR_FORMAT_BY_EXT)}",
        )

    file_bytes = await file.read()
    if len(file_bytes) > _MAX_AVATAR_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"Ukuran file melebihi {_MAX_AVATAR_SIZE_MB}MB")

    try:
        image = Image.open(io.BytesIO(file_bytes))
        detected_format = image.format
        image.verify()
    except Exception:
        raise HTTPException(status_code=400, detail="File tidak dapat dibaca sebagai gambar yang valid")

    if detected_format != _AVATAR_FORMAT_BY_EXT[ext]:
        raise HTTPException(status_code=400, detail="Isi file tidak sesuai dengan ekstensi yang diklaim")

    old_object_key = user.avatar_object_key
    user.avatar_object_key = storage.upload_avatar_file(file_bytes, file.filename or f"avatar.{ext}", str(user.id))
    db.commit()
    db.refresh(user)

    if old_object_key:
        storage.delete_file(old_object_key)  # best-effort, sudah menelan ClientError di dalamnya

    return user


def delete_avatar(db: Session, user: User) -> User:
    if user.avatar_object_key:
        storage.delete_file(user.avatar_object_key)
        user.avatar_object_key = None
        db.commit()
        db.refresh(user)
    return user
