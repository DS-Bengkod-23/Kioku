import os
import uuid
import logging
import tempfile

from sqlalchemy.orm import joinedload

from app.worker import celery_app
from app.database import SessionLocal
from app.config import settings
from app.models.recording import Recording, ProcessingStatus
from app.models.transcript import Transcript
from app.models.meeting import Meeting, MeetingStatus
from app.models.participant import MeetingParticipant
from app.services.storage import get_minio_client
from app.services import notulen as notulen_service

logger = logging.getLogger(__name__)

# Setting yang dibaca modul ml/. Butuh setting baru di ML? Tambah namanya di sini
# (dan di config.py + .env.example), tidak perlu mengubah apa pun di tempat lain.
_ML_ENV_KEYS = (
    "HF_TOKEN",
    "LLM_PROVIDER",
    "GEMINI_API_KEY",
    "GEMINI_MODEL",
    "OPENAI_API_KEY",
    "OPENAI_TRANSCRIBE_MODEL",
    "OPENAI_MODEL",
    "LLM_TRANSCRIBE_TIMEOUT_SECONDS",
    "LLM_EXTRACT_TIMEOUT_SECONDS",
)


class MLPipelineError(Exception):
    """Raised when the ML pipeline itself fails, so Celery records the task as
    failed instead of succeeded even though we already persisted the failure
    to the Recording row via _mark_failed()."""


def _mark_failed(db, recording: Recording, error_message: str) -> None:
    recording.processing_status = ProcessingStatus.failed
    recording.error_message = error_message
    db.commit()


def _set_step(db, recording: Recording, step: str, status_after: ProcessingStatus) -> None:
    steps = dict(recording.processing_steps or {})
    steps[step] = "completed"
    recording.processing_steps = steps
    recording.processing_status = status_after
    db.commit()


@celery_app.task(
    bind=True,
    max_retries=settings.PIPELINE_MAX_RETRIES,
    retry_backoff=settings.PIPELINE_RETRY_BACKOFF_SECONDS,
    retry_backoff_max=settings.PIPELINE_RETRY_BACKOFF_MAX_SECONDS,
    # Tanpa batas ini, koneksi yang hang (network stall ke OpenAI/Gemini/HF, bukan
    # error — cuma diam) bisa memblokir worker tanpa batas waktu. Nilai default
    # (3 jam soft / 3.5 jam hard) sengaja longgar supaya tidak membunuh audio 2 jam
    # yang memang sah masih diproses. Soft = SoftTimeLimitExceeded (bisa ditangkap
    # untuk cleanup), hard = task dibunuh.
    soft_time_limit=settings.PIPELINE_SOFT_TIME_LIMIT_SECONDS,
    time_limit=settings.PIPELINE_TIME_LIMIT_SECONDS,
)
def process_recording_task(self, recording_id: str, meeting_id: str):
    # ml.* di-import lazy (bukan level-modul) karena module ini juga di-import oleh
    # backend-api (lewat upload_recording()'s `.delay()` call), dan container
    # backend-api tidak punya folder ml/ di image-nya (beda build context dari
    # celery-worker) — import level-modul di sini akan meledakkan endpoint upload.
    from ml.errors import PermanentMLError  # noqa: PLC0415

    db = SessionLocal()
    tmp_path = None

    try:
        recording = db.query(Recording).filter(
            Recording.id == uuid.UUID(recording_id)
        ).first()
        if not recording:
            logger.error("Recording %s not found", recording_id)
            return

        # ml/ tidak boleh meng-import backend (lihat ml/env.py), jadi settings-nya
        # disalin ke os.environ supaya ML bisa membacanya lewat os.getenv().
        for name in _ML_ENV_KEYS:
            os.environ.setdefault(name, str(getattr(settings, name)))

        # Step 1: mark upload done, start transcribing
        _set_step(db, recording, "upload", ProcessingStatus.transcribing)

        # Step 2: download audio from MinIO to a temp file
        ext = recording.file_url.rsplit(".", 1)[-1].lower() if "." in recording.file_url else "bin"
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=f".{ext}")
        os.close(tmp_fd)

        client = get_minio_client()
        client.download_file(settings.MINIO_BUCKET, recording.file_url, tmp_path)

        # Step 3: transcribe (PLACEHOLDER)
        try:
            from ml.transcribe import transcribe  # noqa: PLC0415
            transcript_result = transcribe(tmp_path)
        except (NotImplementedError, ImportError) as e:
            logger.error("TRANSCRIBE IMPORT ERROR: %s", e, exc_info=True)
            _mark_failed(db, recording, "ML pipeline not yet implemented")
            raise MLPipelineError("Transcribe failed: ML pipeline not yet implemented") from e

        # Step 4: mark transcribe done, start diarizing
        _set_step(db, recording, "transcribe", ProcessingStatus.diarizing)

        # Step 5: diarize (PLACEHOLDER)
        try:
            from ml.diarize import diarize, merge_transcript_diarization  # noqa: PLC0415
            diarization = diarize(tmp_path)
            merged = merge_transcript_diarization(transcript_result, diarization)
        except (NotImplementedError, ImportError) as e:
            logger.error("DIARIZE IMPORT ERROR: %s", e, exc_info=True)
            _mark_failed(db, recording, "ML pipeline not yet implemented")
            raise MLPipelineError("Diarize failed: ML pipeline not yet implemented") from e

        # Step 6: mark diarize done, start extracting
        _set_step(db, recording, "diarize", ProcessingStatus.extracting)

        # Step 7: extract summary and action items (PLACEHOLDER)
        # Eager-load participants.user & .invitation sekaligus supaya pencocokan
        # nama assignee tidak lazy-load per peserta (N+1 query).
        meeting = (
            db.query(Meeting)
            .options(
                joinedload(Meeting.participants).joinedload(MeetingParticipant.user),
                joinedload(Meeting.participants).joinedload(MeetingParticipant.invitation),
            )
            .filter(Meeting.id == uuid.UUID(meeting_id))
            .first()
        )
        participants = list(meeting.participants)
        participant_names = [
            p.user.name if p.user else p.email for p in participants
        ]

        segments = getattr(merged, "segments", [])
        # Sertakan label speaker (bukan hanya .text) supaya LLM bisa mengaitkan
        # keputusan/tugas ke pembicara yang tepat saat extract_summary/extract_action_items.
        transcript_text = "\n".join(
            f"{seg.get('speaker', '') if isinstance(seg, dict) else getattr(seg, 'speaker', '')}: "
            f"{seg.get('text', '') if isinstance(seg, dict) else getattr(seg, 'text', '')}"
            for seg in segments
        )

        try:
            from ml.extract import extract_summary, extract_action_items  # noqa: PLC0415
            summary_result = extract_summary(transcript_text)
            action_items_result = extract_action_items(transcript_text, participant_names)
        except (NotImplementedError, ImportError) as e:
            logger.error("EXTRACT IMPORT ERROR: %s", e, exc_info=True)
            _mark_failed(db, recording, "ML pipeline not yet implemented")
            raise MLPipelineError("Extract failed: ML pipeline not yet implemented") from e

        # Step 8: simpan Transcript, lalu hasil AI sebagai DRAFT notulen.
        # Notulen tidak dikirim di sini: organizer memeriksanya dulu, email + PDF
        # baru keluar saat dia klik Publikasikan (lihat services/notulen.py).
        # Baris sisa dari percobaan sebelumnya (Celery retry) dibersihkan supaya
        # tidak menabrak unique meeting_id; save_ai_results membersihkan Summary
        # dan action item AI-nya sendiri (action item manual organizer dipertahankan).
        db.query(Transcript).filter(Transcript.meeting_id == uuid.UUID(meeting_id)).delete()
        db.add(
            Transcript(
                meeting_id=uuid.UUID(meeting_id),
                segments=[
                    seg if isinstance(seg, dict) else seg.model_dump()
                    for seg in segments
                ],
            )
        )
        notulen_service.save_ai_results(
            db, meeting, participants, summary_result, action_items_result
        )
        db.commit()

        # Step 9: kunci absensi + tandai rapat selesai (tidak menunggu publish)
        meeting.attendance_locked = True
        meeting.status = MeetingStatus.completed
        db.commit()

        _set_step(db, recording, "extract", ProcessingStatus.completed)

    except Exception as exc:
        logger.exception("process_recording_task failed for recording %s", recording_id)

        # MLPipelineError sendiri sudah permanen (di-raise dari branch NotImplementedError/
        # ImportError di atas) — jangan cocokkan cuma isinstance(exc, PermanentMLError),
        # karena MLPipelineError bukan subclass-nya dan dulu malah lolos ke retry di bawah.
        is_permanent = isinstance(exc, (PermanentMLError, MLPipelineError))
        # Error transient (network/rate-limit/dll) jangan langsung ditandai failed —
        # itu bikin status sempat "failed" di polling frontend padahal retry berikutnya
        # akan sukses. Hanya tandai failed kalau ini memang permanen atau retry sudah habis.
        is_final_attempt = is_permanent or self.request.retries >= self.max_retries

        if is_final_attempt:
            try:
                # exc bisa saja berasal dari db.commit() yang gagal (mis. IntegrityError
                # di step 8) — session harus di-rollback dulu sebelum dipakai lagi, kalau
                # tidak, query di bawah ini ikut gagal dan recording tidak pernah ditandai
                # failed (stuck diam-diam di status sebelumnya selamanya).
                db.rollback()
                rec = db.query(Recording).filter(Recording.id == uuid.UUID(recording_id)).first()
                if rec:
                    _mark_failed(db, rec, str(exc))
            except Exception:
                logger.exception(
                    "Gagal mencatat status failed untuk recording %s setelah error asli di atas",
                    recording_id,
                )

        if isinstance(exc, MLPipelineError):
            raise
        if isinstance(exc, PermanentMLError):
            raise MLPipelineError(str(exc)) from exc
        raise self.retry(exc=exc)
    finally:
        db.close()
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
