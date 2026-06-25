from datetime import datetime, timezone
from fpdf import FPDF

from app.models.meeting import Meeting
from app.models.summary import Summary
from app.models.action_item import ActionItem
from app.models.participant import MeetingParticipant
from app.models.attendance import AttendanceStatus

LOCALE_DAYS = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
LOCALE_MONTHS = [
    "", "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember",
]


def _fmt_date(dt: datetime) -> str:
    day = LOCALE_DAYS[dt.weekday()]
    return f"{day}, {dt.day} {LOCALE_MONTHS[dt.month]} {dt.year}, {dt.strftime('%H:%M')}"


def _fmt_date_short(d) -> str:
    """Format date object (from action_item.due_date)."""
    if d is None:
        return "-"
    return f"{d.day} {LOCALE_MONTHS[d.month]} {d.year}"


def _attendance_label(participant: MeetingParticipant) -> str:
    if participant.attendance is None:
        return "Belum Hadir"
    status = participant.attendance.status
    if status == AttendanceStatus.hadir:
        return "Hadir"
    if status == AttendanceStatus.tidak_hadir:
        return "Tidak Hadir"
    return "Belum Hadir"


def generate_notulen_pdf(
    meeting: Meeting,
    organizer_name: str,
    participants: list[MeetingParticipant],
    summary: Summary,
    action_items: list[ActionItem],
) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # ── HEADER ──────────────────────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 8, "NOTULEN RAPAT", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, "MeetMate", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    pdf.set_line_width(0.5)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(6)

    # ── INFO RAPAT ────────────────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(35, 6, "Judul")
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 6, f": {meeting.title}")

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(35, 6, "Tanggal")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f": {_fmt_date(meeting.scheduled_at)}", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(35, 6, "Lokasi")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f": {meeting.location or '-'}", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(35, 6, "Dipimpin")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f": {organizer_name}", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(4)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(6)

    # ── PESERTA ───────────────────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "PESERTA", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    col_no = 10
    col_name = 100
    col_status = 40

    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(col_no, 6, "No", border=1, fill=True)
    pdf.cell(col_name, 6, "Nama", border=1, fill=True)
    pdf.cell(col_status, 6, "Status", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 9)
    for i, p in enumerate(participants, start=1):
        name = p.user.name if p.user else p.email
        status_label = _attendance_label(p)
        pdf.cell(col_no, 6, str(i), border=1)
        pdf.cell(col_name, 6, name, border=1)
        pdf.cell(col_status, 6, status_label, border=1, new_x="LMARGIN", new_y="NEXT")

    pdf.ln(6)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(6)

    # ── RINGKASAN ─────────────────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "RINGKASAN", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 6, summary.tldr or "-")

    pdf.ln(4)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(6)

    # ── KEPUTUSAN ─────────────────────────────────────────────────────────
    decisions = summary.decisions or []
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "KEPUTUSAN", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 10)
    if decisions:
        for idx, d in enumerate(decisions, start=1):
            pdf.multi_cell(0, 6, f"{idx}. {d}")
    else:
        pdf.cell(0, 6, "-", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(4)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(6)

    # ── TOPIK ─────────────────────────────────────────────────────────────
    topics = summary.topics or []
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "TOPIK YANG DIBAHAS", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 10)
    if topics:
        for t in topics:
            pdf.multi_cell(0, 6, f"  •  {t}")
    else:
        pdf.cell(0, 6, "-", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(4)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(6)

    # ── ACTION ITEMS ──────────────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "ACTION ITEMS", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    col_ai_no = 10
    col_ai_task = 90
    col_ai_pic = 50
    col_ai_due = 40

    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(col_ai_no, 6, "No", border=1, fill=True)
    pdf.cell(col_ai_task, 6, "Tugas", border=1, fill=True)
    pdf.cell(col_ai_pic, 6, "PIC", border=1, fill=True)
    pdf.cell(col_ai_due, 6, "Tenggat", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 9)
    if action_items:
        for i, ai in enumerate(action_items, start=1):
            pic = "-"
            if ai.assignee_participant and ai.assignee_participant.user:
                pic = ai.assignee_participant.user.name
            due = _fmt_date_short(ai.due_date)
            pdf.cell(col_ai_no, 6, str(i), border=1)
            pdf.cell(col_ai_task, 6, ai.task[:55] + ("..." if len(ai.task) > 55 else ""), border=1)
            pdf.cell(col_ai_pic, 6, pic, border=1)
            pdf.cell(col_ai_due, 6, due, border=1, new_x="LMARGIN", new_y="NEXT")
    else:
        pdf.cell(0, 6, "-", new_x="LMARGIN", new_y="NEXT")

    # ── FOOTER ────────────────────────────────────────────────────────────
    pdf.ln(8)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 8)
    timestamp = datetime.now(timezone.utc).strftime("%d %b %Y %H:%M UTC")
    pdf.cell(0, 5, f"Dibuat otomatis oleh MeetMate  ·  {timestamp}", align="C")

    return bytes(pdf.output())
