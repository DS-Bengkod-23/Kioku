import uuid
from datetime import datetime, timedelta
from pathlib import Path
from fpdf import FPDF
from fpdf.enums import MethodReturnValue

from app.config import settings
from app.models.meeting import Meeting
from app.models.summary import Summary
from app.models.action_item import ActionItem
from app.models.participant import MeetingParticipant
from app.models.attendance import AttendanceStatus

_FONT_DIR = "/usr/share/fonts/truetype/dejavu"

LOCALE_MONTHS = [
    "", "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember",
]


def _fmt_date_slash(dt: datetime) -> str:
    return dt.strftime("%d/%m/%Y")


def _fmt_time_wib(dt: datetime) -> str:
    return f"{dt.strftime('%H:%M')} WIB"


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


class NotulenPDF(FPDF):
    """FPDF subclass carrying the running header/footer, suppressed on the cover page."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.header_title = ""
        self.header_date = ""
        self.alias_nb_pages()

    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("DejaVuSans", "B", 9)
        self.cell(95, 5, self.header_title)
        self.set_font("DejaVuSans", "", 9)
        self.cell(95, 5, self.header_date, align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_line_width(0.3)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(4)

    def footer(self):
        if self.page_no() == 1:
            return
        self.set_y(-15)
        self.set_line_width(0.2)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(1)
        self.set_font("DejaVuSans", "", 8)
        self.cell(95, 5, "Minutes of Meeting")
        self.cell(95, 5, f"Page {self.page_no()}/{{nb}}", align="R")


_BODY_INDENT = 6


def _field(pdf: NotulenPDF, label: str, value: str, label_w: int = 45) -> None:
    """Renders 'Label : Value' the way the university template does, wrapping long values."""
    pdf.set_font("DejaVuSans", "", 10)
    pdf.set_x(pdf.l_margin + _BODY_INDENT)
    pdf.cell(label_w, 6, label)
    pdf.multi_cell(0, 6, f": {value}", new_x="LMARGIN", new_y="NEXT")


def _section_heading(pdf: NotulenPDF, heading: str) -> None:
    pdf.set_font("DejaVuSans", "B", 11)
    pdf.cell(0, 7, heading, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)


def _table_row(
    pdf: NotulenPDF,
    x_start: float,
    values: list[str],
    widths: list[int],
    aligns: list[str] | None = None,
    line_h: int = 6,
    fill: bool = False,
) -> None:
    """Draws one table row using the font already set by the caller. Long text wraps
    onto extra lines inside its own cell instead of overflowing into the next column;
    row height grows to fit whichever cell wrapped the most."""
    aligns = aligns or ["L"] * len(values)

    wrapped = [
        pdf.multi_cell(w, line_h, str(text), dry_run=True, output=MethodReturnValue.LINES) or [""]
        for text, w in zip(values, widths)
    ]
    row_h = max(len(lines) for lines in wrapped) * line_h

    if pdf.get_y() + row_h > pdf.page_break_trigger:
        pdf.add_page()

    y0 = pdf.get_y()
    x = x_start
    for lines, w, align in zip(wrapped, widths, aligns):
        pdf.rect(x, y0, w, row_h, style="DF" if fill else "D")
        pdf.set_xy(x, y0)
        pdf.multi_cell(w, line_h, "\n".join(lines), align=align, border=0)
        x += w

    pdf.set_xy(x_start, y0 + row_h)


def generate_notulen_pdf(
    meeting: Meeting,
    organizer_name: str,
    participants: list[MeetingParticipant],
    summary: Summary,
    action_items: list[ActionItem],
    viewer_participant_id: uuid.UUID | None = None,
) -> bytes:
    # Peserta (bukan organizer) cuma boleh lihat action item miliknya sendiri di
    # notulen — samakan dengan filter yang sudah dipakai get_checkin_info().
    if viewer_participant_id is not None:
        action_items = [
            ai for ai in action_items if ai.assignee_participant_id == viewer_participant_id
        ]

    pdf = NotulenPDF()
    pdf.add_font("DejaVuSans", "", f"{_FONT_DIR}/DejaVuSans.ttf")
    pdf.add_font("DejaVuSans", "B", f"{_FONT_DIR}/DejaVuSans-Bold.ttf")
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.header_title = meeting.title.upper()[:60]
    pdf.header_date = f"Tanggal Pertemuan {_fmt_date_slash(meeting.scheduled_at)}"

    # ── COVER PAGE ───────────────────────────────────────────────────────────
    pdf.add_page()

    logo_path = Path(settings.ORG_LOGO_PATH) if settings.ORG_LOGO_PATH else None
    has_logo = logo_path is not None and logo_path.is_file()
    if has_logo:
        pdf.image(str(logo_path), x=pdf.l_margin, y=pdf.get_y(), h=14)
        pdf.set_xy(pdf.l_margin + 18, pdf.get_y() + 4)
        pdf.set_font("DejaVuSans", "B", 11)
        pdf.cell(0, 8, settings.ORG_NAME, align="L", new_x="LMARGIN", new_y="NEXT")
        pdf.set_y(pdf.get_y() + 4)
    else:
        pdf.set_font("DejaVuSans", "B", 12)
        pdf.cell(0, 14, settings.ORG_NAME, align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_line_width(0.8)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(24)

    pdf.set_font("DejaVuSans", "B", 18)
    pdf.multi_cell(0, 9, meeting.title.upper(), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    pdf.set_font("DejaVuSans", "B", 13)
    pdf.cell(0, 8, "MINUTES OF MEETING", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)
    pdf.set_line_width(0.3)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(8)

    pdf.set_font("DejaVuSans", "", 11)
    for line in (
        f"Tanggal Pertemuan: {_fmt_date_slash(meeting.scheduled_at)}",
        f"Lokasi Pertemuan: {meeting.location or '-'}",
        f"Diinisiasi oleh: {organizer_name}",
    ):
        pdf.cell(0, 7, line, align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_y(pdf.h - 25)
    pdf.set_line_width(0.8)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())

    # ── CONTENT PAGES ─────────────────────────────────────────────────────────
    pdf.add_page()

    # RINGKASAN (fitur MeetMate, di luar format resmi kampus, ditaruh sebelum struktur bernomor)
    _section_heading(pdf, "RINGKASAN")
    pdf.set_font("DejaVuSans", "", 10)
    pdf.set_x(pdf.l_margin + _BODY_INDENT)
    pdf.multi_cell(0, 6, summary.tldr or "-", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # 1 PESERTA
    _section_heading(pdf, "1  PESERTA")

    peserta_widths = [10, 42, 33, 27, 23, 25, 20]
    peserta_aligns = ["C", "L", "L", "L", "L", "L", "C"]
    table_x = pdf.l_margin + _BODY_INDENT

    pdf.set_line_width(0.15)
    pdf.set_font("DejaVuSans", "B", 8)
    pdf.set_fill_color(230, 230, 230)
    _table_row(
        pdf, table_x,
        ["No", "Nama", "Jabatan", "Unit", "Telepon", "Status", "Paraf"],
        peserta_widths, aligns=peserta_aligns, fill=True,
    )

    pdf.set_font("DejaVuSans", "", 8)
    for i, p in enumerate(participants, start=1):
        name = p.user.name if p.user else p.email
        jabatan = p.user.job_title if (p.user and p.user.job_title) else "-"
        unit = p.user.department if (p.user and p.user.department) else "-"
        _table_row(
            pdf, table_x,
            [str(i), name, jabatan, unit, "", _attendance_label(p), ""],
            peserta_widths, aligns=peserta_aligns,
        )

    pdf.ln(6)

    # 2 LOKASI PERTEMUAN
    _section_heading(pdf, "2  LOKASI PERTEMUAN")
    _field(pdf, "Gedung", meeting.location_building or "-")
    _field(pdf, "Ruang", meeting.location_room or "-")
    _field(pdf, "Instansi", settings.ORG_NAME)
    _field(pdf, "Kabupaten/Kota", meeting.location_city or "-")
    pdf.ln(4)

    # 3 MULAI PERTEMUAN
    start_time = _fmt_time_wib(meeting.scheduled_at)
    _section_heading(pdf, "3  MULAI PERTEMUAN")
    _field(pdf, "Rencana Awal", start_time)
    _field(pdf, "Aktual Pertemuan", start_time)
    _field(pdf, "Notulen", organizer_name)
    pdf.ln(4)

    # 4 AGENDA PERTEMUAN (data sama seperti "topik yang dibahas")
    topics = summary.topics or []
    _section_heading(pdf, "4  AGENDA PERTEMUAN")
    pdf.set_font("DejaVuSans", "", 10)
    if topics:
        for t in topics:
            pdf.set_x(pdf.l_margin + _BODY_INDENT)
            pdf.multi_cell(0, 6, f"•  {t}", new_x="LMARGIN", new_y="NEXT")
    else:
        pdf.set_x(pdf.l_margin + _BODY_INDENT)
        pdf.cell(0, 6, "-", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # 5 SELESAI PERTEMUAN
    end_dt = meeting.scheduled_at + timedelta(minutes=meeting.duration_minutes)
    end_time = _fmt_time_wib(end_dt)
    _section_heading(pdf, "5  SELESAI PERTEMUAN")
    _field(pdf, "Rencana Selesai", end_time)
    _field(pdf, "Aktual Selesai", end_time)
    pdf.ln(4)

    # 6 RENCANA AKSI PASCA PERTEMUAN (data sama seperti "action items")
    _section_heading(pdf, "6  RENCANA AKSI PASCA PERTEMUAN")

    aksi_widths = [10, 82, 50, 40]
    aksi_aligns = ["C", "L", "L", "L"]
    table_x = pdf.l_margin + _BODY_INDENT

    pdf.set_line_width(0.15)
    pdf.set_font("DejaVuSans", "B", 9)
    pdf.set_fill_color(230, 230, 230)
    _table_row(
        pdf, table_x,
        ["No", "Aksi", "Ditugaskan ke-", "Batas Waktu"],
        aksi_widths, aligns=aksi_aligns, fill=True,
    )

    pdf.set_font("DejaVuSans", "", 9)
    if action_items:
        for i, ai in enumerate(action_items, start=1):
            pic = "-"
            if ai.assignee_participant and ai.assignee_participant.user:
                pic = ai.assignee_participant.user.name
            due = _fmt_date_short(ai.due_date)
            _table_row(
                pdf, table_x,
                [str(i), ai.task, pic, due],
                aksi_widths, aligns=aksi_aligns,
            )
    else:
        pdf.set_x(table_x)
        pdf.cell(0, 6, "-", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    # 7 KEPUTUSAN PERTEMUAN (data sama seperti "keputusan")
    decisions = summary.decisions or []
    _section_heading(pdf, "7  KEPUTUSAN PERTEMUAN")
    pdf.set_font("DejaVuSans", "", 10)
    if decisions:
        for idx, d in enumerate(decisions, start=1):
            pdf.set_x(pdf.l_margin + _BODY_INDENT)
            pdf.multi_cell(0, 6, f"{idx}. {d}", new_x="LMARGIN", new_y="NEXT")
    else:
        pdf.set_x(pdf.l_margin + _BODY_INDENT)
        pdf.cell(0, 6, "-", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # 8 PERTEMUAN BERIKUTNYA (belum ada datanya di sistem, statis dulu)
    _section_heading(pdf, "8  PERTEMUAN BERIKUTNYA")
    _field(pdf, "Lokasi", "-")
    _field(pdf, "Tanggal", "-")
    _field(pdf, "Waktu", "-")

    return bytes(pdf.output())
