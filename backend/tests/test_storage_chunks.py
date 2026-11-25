import io

import pytest
from botocore.exceptions import ClientError

from app.services import storage


class _FakeS3:
    """Klien S3 minimal: cukup untuk helper potongan (put/get/list paginated/delete batch)."""

    def __init__(self, page_size: int = 1000):
        self.objects: dict[str, bytes] = {}
        self.page_size = page_size
        self.delete_batches: list[list[str]] = []

    def put_object(self, Bucket, Key, Body, ContentLength=None):
        self.objects[Key] = bytes(Body)

    def get_object(self, Bucket, Key):
        if Key not in self.objects:
            raise ClientError({"Error": {"Code": "NoSuchKey", "Message": "missing"}}, "GetObject")
        return {"Body": io.BytesIO(self.objects[Key])}

    def get_paginator(self, name):
        assert name == "list_objects_v2"
        return self

    def paginate(self, Bucket, Prefix):
        keys = sorted(key for key in self.objects if key.startswith(Prefix))
        if not keys:
            yield {}  # S3 sungguhan: halaman tanpa kunci "Contents"
            return
        for start in range(0, len(keys), self.page_size):
            yield {
                "Contents": [
                    {"Key": key, "Size": len(self.objects[key])} for key in keys[start : start + self.page_size]
                ]
            }

    def delete_objects(self, Bucket, Delete):
        batch = [item["Key"] for item in Delete["Objects"]]
        self.delete_batches.append(batch)
        for key in batch:
            self.objects.pop(key, None)
        return {}


@pytest.fixture
def fake_s3(monkeypatch):
    client = _FakeS3(page_size=2)
    monkeypatch.setattr(storage, "get_minio_client", lambda: client)
    return client


def test_put_then_get_bytes_roundtrip(fake_s3):
    storage.put_bytes("recording-sessions/s1/000000", b"\x1a\x45\xdf\xa3")

    assert storage.get_bytes("recording-sessions/s1/000000") == b"\x1a\x45\xdf\xa3"


def test_get_bytes_missing_key_raises_file_not_found(fake_s3):
    with pytest.raises(FileNotFoundError):
        storage.get_bytes("recording-sessions/s1/000009")


def test_list_objects_returns_sorted_key_and_size_across_pages(fake_s3):
    for index in (3, 0, 2, 1, 4):
        storage.put_bytes(f"recording-sessions/s1/{index:06d}", b"x" * (index + 1))
    storage.put_bytes("recording-sessions/s2/000000", b"other-session")

    listed = storage.list_objects("recording-sessions/s1/")

    assert listed == [(f"recording-sessions/s1/{index:06d}", index + 1) for index in range(5)]


def test_list_objects_with_nothing_stored_returns_empty_list(fake_s3):
    assert storage.list_objects("recording-sessions/none/") == []


def test_delete_prefix_removes_only_that_prefix_in_batches_of_at_most_1000(fake_s3):
    for index in range(1500):
        storage.put_bytes(f"recording-sessions/s1/{index:06d}", b"x")
    storage.put_bytes("recording-sessions/s2/000000", b"keep")

    storage.delete_prefix("recording-sessions/s1/")

    assert list(fake_s3.objects) == ["recording-sessions/s2/000000"]
    assert fake_s3.delete_batches and all(len(batch) <= 1000 for batch in fake_s3.delete_batches)
    assert sum(len(batch) for batch in fake_s3.delete_batches) == 1500


def test_delete_prefix_on_empty_prefix_is_a_noop(fake_s3):
    storage.delete_prefix("recording-sessions/none/")

    assert fake_s3.delete_batches == []


def test_fake_storage_fixture_mirrors_real_helpers(fake_storage):
    # Menjaga fixture tetap setia pada kontrak helper asli, karena tes tahap-tahap
    # berikutnya bergantung padanya alih-alih pada MinIO.
    storage.put_bytes("recording-sessions/s1/000001", b"bb")
    storage.put_bytes("recording-sessions/s1/000000", b"a")
    storage.put_bytes("recording-sessions/s2/000000", b"other")

    assert storage.get_bytes("recording-sessions/s1/000000") == b"a"
    assert storage.list_objects("recording-sessions/s1/") == [
        ("recording-sessions/s1/000000", 1),
        ("recording-sessions/s1/000001", 2),
    ]

    storage.delete_prefix("recording-sessions/s1/")

    assert storage.list_objects("recording-sessions/s1/") == []
    assert storage.get_bytes("recording-sessions/s2/000000") == b"other"
    with pytest.raises(FileNotFoundError):
        storage.get_bytes("recording-sessions/s1/000000")
