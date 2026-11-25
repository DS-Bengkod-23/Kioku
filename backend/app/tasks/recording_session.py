import uuid

from app.config import settings
from app.database import SessionLocal
from app.services import recording_session as session_service
from app.worker import celery_app


@celery_app.task(
    bind=True,
    # Tanpa retry otomatis: kegagalan dicatat di sesi (`failed` + pesan) dan organizer
    # mencoba ulang lewat endpoint finish. Batas waktu memakai setelan pipeline.
    soft_time_limit=settings.PIPELINE_SOFT_TIME_LIMIT_SECONDS,
    time_limit=settings.PIPELINE_TIME_LIMIT_SECONDS,
)
def finalize_recording_session_task(self, session_id: str):
    db = SessionLocal()
    try:
        session_service.finalize_session(db, uuid.UUID(session_id))
    finally:
        db.close()


@celery_app.task
def sweep_recording_sessions_task():
    """Dijalankan Celery beat tiap RECORDING_SWEEP_INTERVAL_MINUTES: finalisasi sesi
    terlantar, antre ulang sesi yang macet di `finalizing`, dan bersihkan potongan
    sesi gagal yang melewati masa simpan."""
    db = SessionLocal()
    try:
        session_service.sweep_abandoned_sessions(db)
        session_service.requeue_stalled_finalizing_sessions(db)
        session_service.cleanup_expired_failed_sessions(db)
    finally:
        db.close()
