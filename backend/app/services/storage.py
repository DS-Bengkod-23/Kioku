import json
import logging
import uuid
import boto3
from botocore.exceptions import ClientError
from app.config import settings

logger = logging.getLogger(__name__)


def get_minio_client():
    client = boto3.client(
        "s3",
        endpoint_url=f"{'https' if settings.MINIO_SECURE else 'http'}://{settings.MINIO_ENDPOINT}",
        aws_access_key_id=settings.MINIO_ACCESS_KEY,
        aws_secret_access_key=settings.MINIO_SECRET_KEY,
    )
    _ensure_bucket_exists(client)
    return client


def _ensure_bucket_exists(client) -> None:
    try:
        client.head_bucket(Bucket=settings.MINIO_BUCKET)
    except ClientError:
        try:
            client.create_bucket(Bucket=settings.MINIO_BUCKET)
        except ClientError:
            pass  # sudah dibuat barusan oleh request lain yang bersamaan


def upload_file(file_bytes: bytes, filename: str, meeting_id: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    object_key = f"recordings/{meeting_id}/{uuid.uuid4()}.{ext}"

    client = get_minio_client()
    client.put_object(
        Bucket=settings.MINIO_BUCKET,
        Key=object_key,
        Body=file_bytes,
        ContentLength=len(file_bytes),
    )
    return object_key


def get_file_stream(object_key: str):
    """Buka object MinIO sebagai stream (botocore StreamingBody), dipakai untuk
    proxy audio playback tanpa expose MinIO langsung ke browser."""
    client = get_minio_client()
    try:
        response = client.get_object(Bucket=settings.MINIO_BUCKET, Key=object_key)
    except ClientError as e:
        logger.error("Gagal membaca objek storage %s", object_key, exc_info=True)
        raise FileNotFoundError(object_key) from e
    return response["Body"]


def upload_avatar_file(file_bytes: bytes, filename: str, user_id: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    object_key = f"avatars/{user_id}/{uuid.uuid4()}.{ext}"

    client = get_minio_client()
    _ensure_avatar_prefix_public_read(client)
    client.put_object(
        Bucket=settings.MINIO_BUCKET,
        Key=object_key,
        Body=file_bytes,
        ContentLength=len(file_bytes),
    )
    return object_key


def _ensure_avatar_prefix_public_read(client) -> None:
    # avatars/* sengaja public-read (beda dari recordings/* yang tetap privat)
    # supaya avatar_url bisa dipasang langsung ke <img src> tanpa header auth.
    # Di-set di sini (tiap upload avatar), bukan cuma saat create_bucket,
    # supaya bucket lama yang sudah ada sebelum fitur ini (kasus dev sekarang)
    # tetap kebagian policy-nya, bukan hanya bucket yang baru dibuat.
    policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"AWS": ["*"]},
            "Action": "s3:GetObject",
            "Resource": f"arn:aws:s3:::{settings.MINIO_BUCKET}/avatars/*",
        }],
    }
    try:
        client.put_bucket_policy(Bucket=settings.MINIO_BUCKET, Policy=json.dumps(policy))
    except ClientError:
        logger.warning("Gagal set bucket policy public-read untuk avatars/*", exc_info=True)


def get_avatar_url(object_key: str) -> str:
    scheme = "https" if settings.MINIO_SECURE else "http"
    return f"{scheme}://{settings.minio_public_endpoint}/{settings.MINIO_BUCKET}/{object_key}"


def delete_file(file_url: str):
    client = get_minio_client()
    try:
        client.delete_object(Bucket=settings.MINIO_BUCKET, Key=file_url)
    except ClientError:
        # Best-effort by design (dipanggil dari path yang sudah commit ke DB),
        # tapi kegagalan tetap harus kelihatan di log — kalau tidak, objek yatim
        # di storage menumpuk tanpa sinyal operasional sama sekali.
        logger.warning("Gagal menghapus objek storage %s", file_url, exc_info=True)
