"""Review notulen (human-in-the-loop): draft AI -> diedit organizer -> dipublikasikan.

Satu-satunya gerbang visibilitas ada di `is_notulen_visible()`; setiap jalur baca
peserta wajib melewatinya.
"""
import uuid
from datetime import date, datetime, timezone

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.action_item import ActionItem, ActionItemSource
from app.models.meeting import Meeting, NotulenStatus
from app.models.notulen_version import NotulenVersion, NotulenVersionKind
from app.models.participant import MeetingParticipant
from app.models.summary import Summary
from app.models.transcript import Transcript
from app.schemas.notulen import NotulenMeta, SummaryUpdateRequest


def is_notulen_visible(meeting: Meeting, user_id: uuid.UUID | None) -> bool:
    return user_id == meeting.organizer_id or meeting.notulen_status == NotulenStatus.published


def needs_review(item: ActionItem) -> bool:
    return item.ai_assignee_text is not None or item.ai_due_date_text is not None


def mark_edited(meeting: Meeting) -> None:
    """Catat bahwa isi notulen berubah. Caller yang commit."""
    meeting.notulen_edited_at = datetime.now(timezone.utc)


def _latest_published(meeting: Meeting) -> NotulenVersion | None:
    published = [v for v in meeting.notulen_versions if v.kind == NotulenVersionKind.published]
    return max(published, key=lambda v: v.version, default=None)


def _has_unsent_changes(meeting: Meeting, latest: NotulenVersion | None) -> bool:
    return (
        meeting.notulen_status == NotulenStatus.published
        and latest is not None
        and meeting.notulen_edited_at is not None
        and meeting.notulen_edited_at > latest.created_at
    )


def build_notulen_meta(meeting: Meeting) -> NotulenMeta:
    latest = _latest_published(meeting)
    return NotulenMeta(
        status=meeting.notulen_status.value if meeting.notulen_status else None,
        current_version=latest.version if latest else None,
        last_published_at=latest.created_at if latest else None,
        edited_at=meeting.notulen_edited_at,
        has_unsent_changes=_has_unsent_changes(meeting, latest),
        needs_review_count=sum(1 for item in meeting.action_items if needs_review(item)),
    )


def save_ai_results(
    db: Session,
    meeting: Meeting,
    participants: list[MeetingParticipant],
    summary_result,
    action_items_result,
) -> Summary:
    """Simpan output ML sebagai draft. Tanpa commit; caller yang commit.

    Nilai AI yang gagal dicocokkan (assignee bukan peserta, tenggat bukan tanggal
    ISO) disimpan di kolom `ai_*` agar organizer melihat penanda "Perlu dicek"
    alih-alih nilainya hilang diam-diam.
    """
    # Action item manual sengaja tidak disentuh: organizer menambahkannya sendiri.
    db.query(ActionItem).filter(
        ActionItem.meeting_id == meeting.id,
        ActionItem.source == ActionItemSource.ai,
    ).delete()
    db.query(Summary).filter(Summary.meeting_id == meeting.id).delete()

    summary = Summary(
        meeting_id=meeting.id,
        tldr=summary_result.tldr,
        decisions=list(summary_result.decisions),
        topics=list(getattr(summary_result, "topics", [])),
    )
    db.add(summary)

    name_to_participant = {(p.user.name if p.user else p.email): p for p in participants}

    ai_items = []
    for item in action_items_result:
        assignee_name = getattr(item, "assignee_name", None) or getattr(item, "assignee", None)
        due_text = getattr(item, "due_date_text", None)

        participant = name_to_participant.get(assignee_name) if assignee_name else None
        ai_assignee_text = assignee_name if assignee_name and participant is None else None

        due = None
        ai_due_date_text = None
        if isinstance(due_text, str) and due_text.strip():
            try:
                due = date.fromisoformat(due_text.strip())
            except ValueError:
                ai_due_date_text = due_text

        db.add(
            ActionItem(
                meeting_id=meeting.id,
                task=item.task,
                assignee_participant_id=participant.id if participant else None,
                due_date=due,
                source=ActionItemSource.ai,
                ai_assignee_text=ai_assignee_text,
                ai_due_date_text=ai_due_date_text,
            )
        )
        ai_items.append(
            {"task": item.task, "assignee_name": assignee_name, "due_date_text": due_text}
        )

    # Output ML apa adanya, sebelum dicocokkan: bahan evaluasi seberapa sering AI dikoreksi.
    db.add(
        NotulenVersion(
            meeting_id=meeting.id,
            kind=NotulenVersionKind.ai,
            version=None,
            created_by=None,
            content={
                "tldr": summary.tldr,
                "decisions": summary.decisions,
                "topics": summary.topics,
                "action_items": ai_items,
            },
        )
    )

    meeting.notulen_status = NotulenStatus.draft
    meeting.notulen_edited_at = None
    return summary


_ORGANIZER_ONLY = "Hanya organizer yang bisa mengedit notulen"


def get_organizer_meeting(db: Session, meeting_id: uuid.UUID, user_id: uuid.UUID) -> Meeting:
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    if meeting.organizer_id != user_id:
        raise HTTPException(status_code=403, detail=_ORGANIZER_ONLY)
    return meeting


def update_summary(
    db: Session, meeting_id: uuid.UUID, user_id: uuid.UUID, data: SummaryUpdateRequest
) -> Summary:
    meeting = get_organizer_meeting(db, meeting_id, user_id)
    summary = meeting.summary
    if summary is None:
        raise HTTPException(status_code=404, detail="Notulen belum tersedia")

    for field, value in data.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(summary, field, value)
    mark_edited(meeting)
    db.commit()
    db.refresh(summary)
    return summary


def rename_speakers(
    db: Session, meeting_id: uuid.UUID, user_id: uuid.UUID, renames: dict[str, str]
) -> Transcript:
    meeting = get_organizer_meeting(db, meeting_id, user_id)
    transcript = meeting.transcript
    if transcript is None:
        raise HTTPException(status_code=404, detail="Notulen belum tersedia")

    existing = {seg.get("speaker") for seg in transcript.segments}
    for label in renames:
        if label not in existing:
            # Validasi semua label sebelum menulis apa pun: rename parsial tidak boleh tersimpan.
            raise HTTPException(status_code=400, detail=f"Speaker '{label}' tidak ada di transkrip")

    # List baru (bukan mutasi in-place) supaya SQLAlchemy mendeteksi perubahan JSONB.
    # Rename tidak memanggil mark_edited: nama speaker tidak masuk email/PDF notulen.
    transcript.segments = [
        {**seg, "speaker": renames.get(seg.get("speaker"), seg.get("speaker"))}
        for seg in transcript.segments
    ]
    db.commit()
    db.refresh(transcript)
    return transcript


def build_published_snapshot(meeting: Meeting) -> dict:
    """Isi notulen yang dikirim ke peserta (bentuk `published` di spec)."""
    summary = meeting.summary
    items = sorted(meeting.action_items, key=lambda item: item.id)
    return {
        "tldr": summary.tldr,
        "decisions": list(summary.decisions),
        "topics": list(summary.topics),
        "action_items": [
            {
                "id": str(item.id),
                "task": item.task,
                "assignee_participant_id": (
                    str(item.assignee_participant_id) if item.assignee_participant_id else None
                ),
                "assignee_name": (
                    (item.assignee_participant.user.name if item.assignee_participant.user
                     else item.assignee_participant.email)
                    if item.assignee_participant
                    else None
                ),
                "due_date": item.due_date.isoformat() if item.due_date else None,
            }
            for item in items
        ],
    }


def version_label(meeting: Meeting) -> str:
    """Label di PDF: draft vs `Versi n` (+ tanggal edit kalau ada perubahan belum terkirim)."""
    if meeting.notulen_status == NotulenStatus.draft:
        return "DRAFT — belum dipublikasikan"
    latest = _latest_published(meeting)
    if meeting.notulen_status != NotulenStatus.published or latest is None:
        return ""
    label = f"Versi {latest.version}"
    if _has_unsent_changes(meeting, latest):
        label += f" · diperbarui {meeting.notulen_edited_at.strftime('%d/%m/%Y')}"
    return label


def _send_new_version(db: Session, meeting: Meeting, user_id: uuid.UUID) -> Meeting:
    """Buat versi published berikutnya lalu antrikan email. Dipakai publish dan kirim ulang."""
    # Tarik max dari DB (bukan dari relasi yang mungkin basi): dua request bersamaan
    # akan sama-sama menghitung n+1, dan unique (meeting_id, version) menolak yang kalah.
    latest_number = (
        db.query(func.max(NotulenVersion.version))
        .filter(
            NotulenVersion.meeting_id == meeting.id,
            NotulenVersion.kind == NotulenVersionKind.published,
        )
        .scalar()
    ) or 0
    version = latest_number + 1

    db.add(
        NotulenVersion(
            meeting_id=meeting.id,
            kind=NotulenVersionKind.published,
            version=version,
            content=build_published_snapshot(meeting),
            created_by=user_id,
        )
    )
    meeting.notulen_status = NotulenStatus.published
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Notulen sedang dikirim, muat ulang halaman")

    # Import lazy (pola upload_recording): task di-import saat dipakai supaya test
    # bisa me-monkeypatch `.delay` tanpa broker Redis.
    from app.tasks.send_notulen import send_notulen_task  # noqa: PLC0415

    send_notulen_task.delay(str(meeting.id), version)
    db.refresh(meeting)
    return meeting


def publish_notulen(db: Session, meeting_id: uuid.UUID, user_id: uuid.UUID) -> Meeting:
    meeting = get_organizer_meeting(db, meeting_id, user_id)
    if meeting.summary is None or meeting.notulen_status is None:
        raise HTTPException(status_code=404, detail="Notulen belum tersedia")
    if meeting.notulen_status != NotulenStatus.draft:
        raise HTTPException(status_code=409, detail="Notulen sudah dipublikasikan")
    return _send_new_version(db, meeting, user_id)


def resend_notulen(db: Session, meeting_id: uuid.UUID, user_id: uuid.UUID) -> Meeting:
    meeting = get_organizer_meeting(db, meeting_id, user_id)
    if meeting.summary is None:
        raise HTTPException(status_code=404, detail="Notulen belum tersedia")
    if meeting.notulen_status != NotulenStatus.published:
        raise HTTPException(status_code=409, detail="Notulen belum dipublikasikan")
    if not build_notulen_meta(meeting).has_unsent_changes:
        raise HTTPException(status_code=409, detail="Tidak ada perubahan sejak versi terakhir")
    return _send_new_version(db, meeting, user_id)
