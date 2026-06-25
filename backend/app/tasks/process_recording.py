import os
import uuid
import logging
import tempfile
from datetime import date

from app.worker import celery_app
from app.database import SessionLocal
from app.config import settings
from app.models.recording import Recording, ProcessingStatus
from app.models.transcript import Transcript
from app.models.summary import Summary
from app.models.action_item import ActionItem
from app.models.meeting import Meeting
from app.services.storage import get_minio_client
from app.services.email import send_notulen_email
from app.services.pdf import generate_notulen_pdf

logger = logging.getLogger(__name__)


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


@celery_app.task(bind=True, max_retries=3)
def process_recording_task(self, recording_id: str, meeting_id: str):
    db = SessionLocal()
    tmp_path = None

    try:
        recording = db.query(Recording).filter(
            Recording.id == uuid.UUID(recording_id)
        ).first()
        if not recording:
            logger.error("Recording %s not found", recording_id)
            return

        # Propagate pydantic settings → os.environ so ML modules can use os.getenv()
        os.environ.setdefault("HF_TOKEN", settings.HF_TOKEN)
        os.environ.setdefault("WHISPER_MODEL", settings.WHISPER_MODEL)
        os.environ.setdefault("LLM_PROVIDER", settings.LLM_PROVIDER)
        os.environ.setdefault("OPENAI_API_KEY", settings.OPENAI_API_KEY)
        os.environ.setdefault("OPENAI_MODEL", settings.OPENAI_MODEL)
        os.environ.setdefault("OLLAMA_BASE_URL", settings.OLLAMA_BASE_URL)
        os.environ.setdefault("OLLAMA_MODEL", settings.OLLAMA_MODEL)

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
            return

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
            return

        # Step 6: mark diarize done, start extracting
        _set_step(db, recording, "diarize", ProcessingStatus.extracting)

        # Step 7: extract summary and action items (PLACEHOLDER)
        meeting = db.query(Meeting).filter(Meeting.id == uuid.UUID(meeting_id)).first()
        participants = list(meeting.participants)
        participant_names = [
            p.user.name if p.user else p.email for p in participants
        ]

        segments = getattr(merged, "segments", [])
        transcript_text = " ".join(
            seg.get("text", "") if isinstance(seg, dict) else getattr(seg, "text", "")
            for seg in segments
        )

        try:
            from ml.extract import extract_summary, extract_action_items  # noqa: PLC0415
            summary_result = extract_summary(transcript_text)
            action_items_result = extract_action_items(transcript_text, participant_names)
        except (NotImplementedError, ImportError) as e:
            logger.error("EXTRACT IMPORT ERROR: %s", e, exc_info=True)
            _mark_failed(db, recording, "ML pipeline not yet implemented")
            return

        # Step 8: save Transcript, Summary, ActionItem to DB
        transcript_obj = Transcript(
            meeting_id=uuid.UUID(meeting_id),
            segments=[
                seg if isinstance(seg, dict) else seg.model_dump()
                for seg in segments
            ],
        )
        db.add(transcript_obj)

        summary_obj = Summary(
            meeting_id=uuid.UUID(meeting_id),
            tldr=summary_result.tldr,
            decisions=summary_result.decisions,
            topics=getattr(summary_result, "topics", []),
        )
        db.add(summary_obj)

        name_to_participant = {
            (p.user.name if p.user else p.email): p for p in participants
        }

        for item in action_items_result:
            assignee_name = getattr(item, "assignee_name", None) or getattr(item, "assignee", None)
            assignee_id = None
            if assignee_name:
                participant = name_to_participant.get(assignee_name)
                if participant:
                    assignee_id = participant.id

            due = getattr(item, "due_date", None)
            if isinstance(due, str):
                try:
                    due = date.fromisoformat(due)
                except ValueError:
                    due = None

            db.add(ActionItem(
                meeting_id=uuid.UUID(meeting_id),
                task=item.task,
                assignee_participant_id=assignee_id,
                due_date=due,
            ))

        db.commit()
        db.refresh(summary_obj)

        # Step 9: mark extract done, start sending email
        _set_step(db, recording, "extract", ProcessingStatus.sending_email)

        # Step 10: generate PDF satu kali, kirim ke semua peserta yang punya invitation token
        db_action_items = db.query(ActionItem).filter(
            ActionItem.meeting_id == uuid.UUID(meeting_id)
        ).all()

        db.refresh(meeting)
        organizer_name = meeting.organizer.name if meeting.organizer else "Organizer"
        pdf_bytes = generate_notulen_pdf(
            meeting=meeting,
            organizer_name=organizer_name,
            participants=participants,
            summary=summary_obj,
            action_items=db_action_items,
        )

        for p in participants:
            if not p.invitation or not p.invitation.token:
                continue
            checkin_url = f"{settings.APP_BASE_URL}/check-in/{p.invitation.token}"
            send_notulen_email(
                recipient_email=p.email,
                recipient_name=p.user.name if p.user else p.email,
                meeting_title=meeting.title,
                scheduled_at=meeting.scheduled_at,
                checkin_url=checkin_url,
                pdf_bytes=pdf_bytes,
                meeting_id=uuid.UUID(meeting_id),
                db=db,
            )

        # Step 11: all done
        _set_step(db, recording, "send_email", ProcessingStatus.completed)

    except Exception as exc:
        logger.exception("process_recording_task failed for recording %s", recording_id)
        try:
            rec = db.query(Recording).filter(Recording.id == uuid.UUID(recording_id)).first()
            if rec:
                _mark_failed(db, rec, str(exc))
        except Exception:
            pass
        raise self.retry(exc=exc)
    finally:
        db.close()
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
