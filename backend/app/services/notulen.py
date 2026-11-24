"""Review notulen (human-in-the-loop): draft AI -> diedit organizer -> dipublikasikan.

Satu-satunya gerbang visibilitas ada di `is_notulen_visible()`; setiap jalur baca
peserta wajib melewatinya.
"""
import uuid
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.models.action_item import ActionItem, ActionItemSource
from app.models.meeting import Meeting, NotulenStatus
from app.models.notulen_version import NotulenVersion, NotulenVersionKind
from app.models.participant import MeetingParticipant
from app.models.summary import Summary
from app.schemas.notulen import NotulenMeta


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
