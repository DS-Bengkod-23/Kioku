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
        except (NotImplementedError, ImportError):
            _mark_failed(db, recording, "ML pipeline not yet implemented")
            return

        # Step 4: mark transcribe done, start diarizing
        _set_step(db, recording, "transcribe", ProcessingStatus.diarizing)

        # Step 5: diarize (PLACEHOLDER)
        try:
            from ml.diarize import diarize, merge_transcript_diarization  # noqa: PLC0415
            diarization = diarize(tmp_path)
            merged = merge_transcript_diarization(transcript_result, diarization)
        except (NotImplementedError, ImportError):
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
        except (NotImplementedError, ImportError):
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

        # Step 10: send notulen email to all participants
        db_action_items = db.query(ActionItem).filter(
            ActionItem.meeting_id == uuid.UUID(meeting_id)
        ).all()

        for p in participants:
            p_action_items = [
                {
                    "task": ai.task,
                    "due_date": ai.due_date.isoformat() if ai.due_date else None,
                }
                for ai in db_action_items
                if ai.assignee_participant_id == p.id
            ]
            send_notulen_email(
                recipient_email=p.email,
                recipient_name=p.user.name if p.user else p.email,
                meeting_title=meeting.title,
                scheduled_at=meeting.scheduled_at,
                summary_tldr=summary_obj.tldr,
                decisions=summary_obj.decisions,
                action_items=p_action_items,
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
