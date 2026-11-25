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


def put_bytes(object_key: str, data: bytes) -> None:
    """Simpan byte pada kunci yang ditentukan pemanggil (dipakai untuk potongan
    rekaman sementara; upload_file membuat kunci acak sendiri)."""
    client = get_minio_client()
    client.put_object(
        Bucket=settings.MINIO_BUCKET,
        Key=object_key,
        Body=data,
        ContentLength=len(data),
    )


def get_bytes(object_key: str) -> bytes:
    """Baca objek utuh ke memori. Hanya untuk objek kecil (satu potongan rekaman)."""
    return get_file_stream(object_key).read()


def list_objects(prefix: str) -> list[tuple[str, int]]:
    """Daftar (kunci, ukuran byte) semua objek berawalan `prefix`, terurut menurut kunci.
    Awalan sebaiknya diakhiri '/' agar `s1/` tidak ikut mengambil `s10/`."""
    client = get_minio_client()
    found: list[tuple[str, int]] = []
    for page in client.get_paginator("list_objects_v2").paginate(Bucket=settings.MINIO_BUCKET, Prefix=prefix):
        for item in page.get("Contents", []):
            found.append((item["Key"], item["Size"]))
    return sorted(found)


def delete_prefix(prefix: str) -> None:
    """Hapus semua objek berawalan `prefix` (batch maksimal 1000 kunci, batas S3).
    Best-effort seperti delete_file: kegagalan dicatat di log, tidak dilempar."""
    keys = [key for key, _ in list_objects(prefix)]
    client = get_minio_client()
    for start in range(0, len(keys), 1000):
        batch = [{"Key": key} for key in keys[start : start + 1000]]
        try:
            client.delete_objects(Bucket=settings.MINIO_BUCKET, Delete={"Objects": batch, "Quiet": True})
        except ClientError:
            logger.warning("Gagal menghapus %d objek storage berawalan %s", len(batch), prefix, exc_info=True)


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
