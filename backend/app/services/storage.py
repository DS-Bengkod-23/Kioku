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


def delete_file(file_url: str):
    client = get_minio_client()
    try:
        client.delete_object(Bucket=settings.MINIO_BUCKET, Key=file_url)
    except ClientError:
        # Best-effort by design (dipanggil dari path yang sudah commit ke DB),
        # tapi kegagalan tetap harus kelihatan di log — kalau tidak, objek yatim
        # di storage menumpuk tanpa sinyal operasional sama sekali.
        logger.warning("Gagal menghapus objek storage %s", file_url, exc_info=True)
