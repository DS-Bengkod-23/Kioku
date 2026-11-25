"""Sesi rekam langsung: browser mengirim potongan audio bertahap, task finalize
(Tahap berikutnya) menggabungkannya. Modul ini menangani mulai, kirim potongan, status."""
import contextlib
import logging
import os
import tempfile
import uuid
from collections.abc import Iterable
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.exceptions import DetailedHTTPException
from app.models.meeting import Meeting
from app.models.recording import Recording
from app.models.recording_session import ACTIVE_STATUSES, RecordingSession, RecordingSessionStatus
from app.services import audio_convert, storage
from app.services import recording as recording_service
from app.services.audio_convert import AudioConversionError

logger = logging.getLogger(__name__)

# Tipe rekaman yang didukung -> ekstensi berkas input untuk ffmpeg.
EXT_BY_MIME = {"audio/webm": "webm", "audio/ogg": "ogg", "audio/mp4": "mp4"}
SUPPORTED_MIME_TYPES = set(EXT_BY_MIME)


def chunk_prefix(session_id: uuid.UUID) -> str:
    # Akhiran "/" supaya awalan satu sesi tidak ikut mengambil sesi lain.
    return f"recording-sessions/{session_id}/"


def chunk_key(session_id: uuid.UUID, index: int) -> str:
    return f"{chunk_prefix(session_id)}{index:06d}"


def max_chunk_count() -> int:
    """Jumlah potongan maksimal = batas durasi / panjang potongan + toleransi persen.
    Hitungan integer (dibulatkan ke atas) agar tidak terkena galat float."""
    numerator = settings.MAX_AUDIO_DURATION_HOURS * 3600 * (100 + settings.RECORDING_CHUNK_COUNT_TOLERANCE_PERCENT)
    denominator = settings.RECORDING_CHUNK_SECONDS * 100
    return -(-numerator // denominator)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _get_meeting_or_404(db: Session, meeting_id: uuid.UUID) -> Meeting:
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id, Meeting.deleted_at.is_(None)).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting tidak ditemukan.")
    return meeting


def _get_session_or_404(db: Session, meeting_id: uuid.UUID, session_id: uuid.UUID) -> RecordingSession:
    session = (
        db.query(RecordingSession)
        .filter(RecordingSession.id == session_id, RecordingSession.meeting_id == meeting_id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Sesi rekaman tidak ditemukan.")
    return session


def _find_active_session(db: Session, meeting_id: uuid.UUID) -> RecordingSession | None:
    return (
        db.query(RecordingSession)
        .filter(RecordingSession.meeting_id == meeting_id, RecordingSession.status.in_(ACTIVE_STATUSES))
        .first()
    )


def _active_session_conflict(session: RecordingSession) -> DetailedHTTPException:
    return DetailedHTTPException(
        status_code=409,
        detail="Sudah ada sesi rekaman aktif untuk meeting ini.",
        extra={"session_id": str(session.id), "chunk_count": session.chunk_count},
    )


def _normalize_mime_type(mime_type: str) -> str:
    # Browser mengirim parameter codec ("audio/webm;codecs=opus"); yang dicocokkan
    # hanya tipe dasarnya.
    base = (mime_type or "").split(";")[0].strip().lower()
    if base not in SUPPORTED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Tipe audio tidak didukung. Gunakan rekaman WebM, Ogg, atau MP4.",
        )
    return base


def start_session(db: Session, meeting_id: uuid.UUID, user_id: uuid.UUID, mime_type: str) -> RecordingSession:
    _get_meeting_or_404(db, meeting_id)
    recording_service._require_organizer(db, meeting_id, user_id)
    normalized_mime = _normalize_mime_type(mime_type)

    existing_recording = db.query(Recording).filter(Recording.meeting_id == meeting_id).first()
    recording_service._reject_if_pipeline_active(existing_recording)

    active = _find_active_session(db, meeting_id)
    if active:
        raise _active_session_conflict(active)

    session = RecordingSession(
        meeting_id=meeting_id,
        user_id=user_id,
        mime_type=normalized_mime,
        status=RecordingSessionStatus.recording.value,
    )
    db.add(session)
    try:
        db.commit()
    except IntegrityError:
        # Dua tab memulai bersamaan: pemeriksaan di atas lolos untuk keduanya, tapi
        # indeks unik database hanya meloloskan satu. Yang kalah tetap dapat info sesi pemenang.
        db.rollback()
        winner = _find_active_session(db, meeting_id)
        if winner is None:
            raise
        raise _active_session_conflict(winner)
    db.refresh(session)
    return session


def store_chunk(
    db: Session,
    meeting_id: uuid.UUID,
    session_id: uuid.UUID,
    user_id: uuid.UUID,
    index: int,
    data: bytes,
) -> int:
    """Simpan satu potongan (idempoten: indeks sama menimpa). Mengembalikan jumlah potongan tersimpan."""
    _get_meeting_or_404(db, meeting_id)
    recording_service._require_organizer(db, meeting_id, user_id)
    session = _get_session_or_404(db, meeting_id, session_id)

    if session.status != RecordingSessionStatus.recording.value:
        raise HTTPException(
            status_code=409,
            detail=f"Sesi rekaman sudah tidak menerima potongan (status: {session.status}).",
        )
    if index < 0 or index >= max_chunk_count():
        raise HTTPException(status_code=400, detail="Indeks potongan di luar rentang yang diizinkan.")
    if not data:
        raise HTTPException(status_code=400, detail="Potongan audio kosong.")
    if len(data) > settings.RECORDING_CHUNK_MAX_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"Potongan melebihi ukuran maksimum {settings.RECORDING_CHUNK_MAX_SIZE_MB}MB.",
        )

    key = chunk_key(session.id, index)
    stored = dict(storage.list_objects(chunk_prefix(session.id)))
    # Menimpa indeks yang sama: ukuran lama diganti ukuran baru, bukan ditambahkan.
    total_after = sum(stored.values()) - stored.get(key, 0) + len(data)
    if total_after > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"Total ukuran rekaman melebihi batas {settings.MAX_UPLOAD_SIZE_MB}MB.",
        )

    storage.put_bytes(key, data)

    session.chunk_count = len(stored) + (0 if key in stored else 1)
    session.last_activity_at = _now()
    db.commit()
    return session.chunk_count


def get_session(
    db: Session, meeting_id: uuid.UUID, session_id: uuid.UUID, user_id: uuid.UUID
) -> RecordingSession:
    _get_meeting_or_404(db, meeting_id)
    recording_service._require_organizer(db, meeting_id, user_id)
    return _get_session_or_404(db, meeting_id, session_id)


def _stored_indices(session_id: uuid.UUID) -> set[int]:
    return {int(key.rsplit("/", 1)[1]) for key, _ in storage.list_objects(chunk_prefix(session_id))}


def finish_session(
    db: Session,
    meeting_id: uuid.UUID,
    session_id: uuid.UUID,
    user_id: uuid.UUID,
    total_chunks: int,
) -> RecordingSession:
    """Tandai sesi selesai dan antre task finalize. Idempoten: sesi yang sudah
    `finalizing`/`finalized` tidak membuat pekerjaan ganda; sesi `failed` dicoba ulang."""
    _get_meeting_or_404(db, meeting_id)
    recording_service._require_organizer(db, meeting_id, user_id)
    session = _get_session_or_404(db, meeting_id, session_id)

    if session.status in (RecordingSessionStatus.finalizing.value, RecordingSessionStatus.finalized.value):
        return session
    if session.status == RecordingSessionStatus.abandoned.value:
        raise HTTPException(
            status_code=409,
            detail="Sesi rekaman ini sudah dibuang (terlantar atau masa simpannya habis). Mulai rekaman baru.",
        )

    if total_chunks < 1 or total_chunks > max_chunk_count():
        raise HTTPException(status_code=400, detail="Jumlah potongan di luar rentang yang diizinkan.")

    stored = _stored_indices(session.id)
    missing = [index for index in range(total_chunks) if index not in stored]
    if missing:
        raise DetailedHTTPException(
            status_code=409,
            detail="Potongan rekaman belum lengkap. Kirim ulang potongan yang hilang lalu selesaikan lagi.",
            extra={"missing_indices": missing},
        )

    # Klaim atomik: hanya satu dari dua permintaan "selesai" serentak yang mengubah
    # status, jadi hanya satu yang mengantre task.
    try:
        claimed = (
            db.query(RecordingSession)
            .filter(
                RecordingSession.id == session.id,
                RecordingSession.status.in_(
                    [RecordingSessionStatus.recording.value, RecordingSessionStatus.failed.value]
                ),
            )
            .update(
                {
                    RecordingSession.status: RecordingSessionStatus.finalizing.value,
                    RecordingSession.chunk_count: total_chunks,
                    RecordingSession.error_message: None,
                    RecordingSession.finished_at: None,
                    RecordingSession.last_activity_at: _now(),
                },
                synchronize_session=False,
            )
        )
        db.commit()
    except IntegrityError:
        # Mencoba ulang sesi `failed` setelah sesi baru sudah dimulai untuk meeting yang sama.
        db.rollback()
        winner = _find_active_session(db, meeting_id)
        if winner is None:
            raise
        raise _active_session_conflict(winner)

    db.refresh(session)
    if claimed:
        # Import lazy: modul task mengimpor modul ini.
        from app.tasks.recording_session import finalize_recording_session_task  # noqa: PLC0415

        finalize_recording_session_task.delay(str(session.id))
    return session


class _ChunkMissingError(Exception):
    def __init__(self, index: int):
        super().__init__(f"Potongan rekaman ke-{index} tidak ditemukan di penyimpanan. Rekam ulang atau hubungi admin.")


def _remove(path: str) -> None:
    with contextlib.suppress(FileNotFoundError):
        os.unlink(path)


def _mark_failed(db: Session, session_id: uuid.UUID, message: str) -> None:
    db.rollback()
    session = db.get(RecordingSession, session_id)
    if session is None or session.status != RecordingSessionStatus.finalizing.value:
        return
    session.status = RecordingSessionStatus.failed.value
    session.error_message = message
    session.finished_at = _now()
    db.commit()


def _merge_and_convert(session: RecordingSession) -> bytes:
    """Gabungkan potongan BYTE DEMI BYTE ke satu berkas sementara lalu konversi sekali
    ke m4a. Hanya potongan pertama yang berisi header, jadi tiap potongan tidak boleh
    dikonversi sendiri-sendiri. Berkas sementara selalu dihapus."""
    src_fd, src_path = tempfile.mkstemp(suffix=f".{EXT_BY_MIME[session.mime_type]}")
    dst_fd, dst_path = tempfile.mkstemp(suffix=".m4a")
    os.close(src_fd)
    os.close(dst_fd)
    try:
        with open(src_path, "wb") as merged:
            for index in range(session.chunk_count):
                try:
                    merged.write(storage.get_bytes(chunk_key(session.id, index)))
                except FileNotFoundError as exc:
                    raise _ChunkMissingError(index) from exc
        audio_convert.convert_to_m4a(
            src_path,
            dst_path,
            sample_rate=settings.RECORDING_OUTPUT_SAMPLE_RATE,
            bitrate_kbps=settings.RECORDING_OUTPUT_BITRATE_KBPS,
        )
        return Path(dst_path).read_bytes()
    finally:
        _remove(src_path)
        _remove(dst_path)


def finalize_session(db: Session, session_id: uuid.UUID) -> None:
    """Dipanggil task Celery. Menggabung + mengonversi potongan lalu menyerahkan hasilnya
    ke jalur penyimpanan hasil yang sama dengan upload manual. Kegagalan apa pun membuat
    sesi `failed` dengan pesan jelas dan potongan dipertahankan untuk percobaan ulang."""
    session = db.get(RecordingSession, session_id)
    if session is None or session.status != RecordingSessionStatus.finalizing.value:
        return  # idempoten: sesi sudah diproses, dibatalkan, atau tidak ada

    try:
        meeting = db.get(Meeting, session.meeting_id)
        if meeting is None:
            raise HTTPException(status_code=404, detail="Meeting tidak ditemukan.")
        existing = db.query(Recording).filter(Recording.meeting_id == meeting.id).first()
        recording_service._reject_if_pipeline_active(existing)

        audio = _merge_and_convert(session)
        recording_service.store_recording_result(
            db, meeting, audio, f"rekaman-{session.id}.m4a", ext="m4a"
        )

        session = db.get(RecordingSession, session_id)
        session.status = RecordingSessionStatus.finalized.value
        session.error_message = None
        session.finished_at = _now()
        db.commit()
    except HTTPException as exc:
        _mark_failed(db, session_id, str(exc.detail))
        return
    except (AudioConversionError, _ChunkMissingError) as exc:
        _mark_failed(db, session_id, str(exc))
        return
    except Exception:
        logger.exception("Finalisasi sesi rekaman %s gagal tak terduga", session_id)
        _mark_failed(db, session_id, "Terjadi kesalahan tak terduga saat memproses rekaman. Coba selesaikan lagi.")
        return

    try:
        storage.delete_prefix(chunk_prefix(session_id))
    except Exception:
        logger.warning("Gagal membersihkan potongan sesi %s", session_id, exc_info=True)


def contiguous_prefix_length(indices: Iterable[int]) -> int:
    """Panjang deret potongan berurutan tanpa celah mulai dari indeks 0.

    {0,1,2,4} -> 3. Potongan setelah celah dibuang karena menggabungkan potongan yang
    bolong bisa merusak berkas (hanya potongan pertama yang membawa header)."""
    present = set(indices)
    length = 0
    while length in present:
        length += 1
    return length


def _transition(db: Session, session_id: uuid.UUID, *, from_statuses: list[str], values: dict, only_before=None) -> bool:
    """Ubah status secara atomik (UPDATE ... WHERE status IN ...). True kalau barisnya
    benar-benar berubah, sehingga hanya satu pelaku (sweep / permintaan finish) yang menang."""
    query = db.query(RecordingSession).filter(
        RecordingSession.id == session_id, RecordingSession.status.in_(from_statuses)
    )
    if only_before is not None:
        # Syarat tambahan: potongan yang masuk sesaat setelah pemindaian membatalkan klaim.
        query = query.filter(RecordingSession.last_activity_at < only_before)
    updated = query.update(values, synchronize_session=False)
    db.commit()
    return updated == 1


def sweep_abandoned_sessions(db: Session) -> list[uuid.UUID]:
    """Sesi `recording` yang tak menerima potongan baru selama batas waktu dianggap terlantar.
    Dengan potongan berurutan dari indeks 0 -> difinalisasi dari deret itu; tanpa -> dibuang.
    Mengembalikan id sesi yang diantre untuk difinalisasi."""
    cutoff = _now() - timedelta(minutes=settings.RECORDING_SESSION_ABANDON_MINUTES)
    stale_ids = [
        row.id
        for row in db.query(RecordingSession.id).filter(
            RecordingSession.status == RecordingSessionStatus.recording.value,
            RecordingSession.last_activity_at < cutoff,
        )
    ]

    queued: list[uuid.UUID] = []
    for session_id in stale_ids:
        usable = contiguous_prefix_length(_stored_indices(session_id))
        recording_only = [RecordingSessionStatus.recording.value]
        if usable == 0:
            if _transition(
                db,
                session_id,
                from_statuses=recording_only,
                only_before=cutoff,
                values={
                    RecordingSession.status: RecordingSessionStatus.abandoned.value,
                    RecordingSession.error_message: "Sesi terlantar tanpa potongan yang dapat dipakai.",
                    RecordingSession.finished_at: _now(),
                },
            ):
                storage.delete_prefix(chunk_prefix(session_id))
        elif _transition(
            db,
            session_id,
            from_statuses=recording_only,
            only_before=cutoff,
            values={
                RecordingSession.status: RecordingSessionStatus.finalizing.value,
                RecordingSession.chunk_count: usable,
                RecordingSession.last_activity_at: _now(),
            },
        ):
            queued.append(session_id)

    if queued:
        from app.tasks.recording_session import finalize_recording_session_task  # noqa: PLC0415

        for session_id in queued:
            finalize_recording_session_task.delay(str(session_id))
    return queued


def requeue_stalled_finalizing_sessions(db: Session) -> list[uuid.UUID]:
    """Sesi `finalizing` yang tak berubah selama RECORDING_FINALIZE_STALE_MINUTES dianggap
    macet (worker mati / task hilang) dan finalize-nya diantre ulang. Tanpa ini sesi itu
    selamanya memblokir rekaman baru lewat indeks unik. Mengembalikan id yang diantre ulang."""
    cutoff = _now() - timedelta(minutes=settings.RECORDING_FINALIZE_STALE_MINUTES)
    stale_ids = [
        row.id
        for row in db.query(RecordingSession.id).filter(
            RecordingSession.status == RecordingSessionStatus.finalizing.value,
            RecordingSession.last_activity_at < cutoff,
        )
    ]

    queued: list[uuid.UUID] = []
    for session_id in stale_ids:
        # Klaim atomik dengan memajukan jam macet: dua sweep serentak tidak mengantre ganda,
        # dan sesi ini baru dianggap macet lagi setelah satu jendela penuh.
        if _transition(
            db,
            session_id,
            from_statuses=[RecordingSessionStatus.finalizing.value],
            only_before=cutoff,
            values={RecordingSession.last_activity_at: _now()},
        ):
            queued.append(session_id)

    if queued:
        from app.tasks.recording_session import finalize_recording_session_task  # noqa: PLC0415

        for session_id in queued:
            finalize_recording_session_task.delay(str(session_id))
    return queued


def cleanup_expired_failed_sessions(db: Session) -> int:
    """Hapus potongan sesi `failed` yang melewati masa simpan. Sesinya ditandai `abandoned`
    (tanpa potongan tak bisa dicoba ulang) supaya tidak dipindai lagi."""
    cutoff = _now() - timedelta(hours=settings.RECORDING_FAILED_RETENTION_HOURS)
    expired_ids = [
        row.id
        for row in db.query(RecordingSession.id).filter(
            RecordingSession.status == RecordingSessionStatus.failed.value,
            RecordingSession.finished_at < cutoff,
        )
    ]

    cleaned = 0
    for session_id in expired_ids:
        # Klaim dulu, hapus kemudian: kalau organizer mencoba ulang sesaat sebelumnya,
        # klaim gagal dan potongannya selamat.
        if _transition(
            db,
            session_id,
            from_statuses=[RecordingSessionStatus.failed.value],
            values={RecordingSession.status: RecordingSessionStatus.abandoned.value},
        ):
            storage.delete_prefix(chunk_prefix(session_id))
            cleaned += 1
    return cleaned
