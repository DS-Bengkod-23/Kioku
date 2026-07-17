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

# DejaVu Serif dipilih (bukan Liberation Serif) karena satu paket font sama
# DejaVu Sans yang dipakai kode sebelumnya (fonts-dejavu-core), jadi kalau di
# server DejaVuSans.ttf sudah ada, DejaVuSerif.ttf otomatis ikut ada juga.
# Tidak perlu install font baru di Docker image.
_FONT_DIR = "/usr/share/fonts/truetype/dejavu"
_FONT_FAMILY = "NotulenSerif"

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
        self.set_font(_FONT_FAMILY, "B", 9)
        self.cell(95, 5, self.header_title)
        self.set_font(_FONT_FAMILY, "", 9)
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
        self.set_font(_FONT_FAMILY, "", 8)
        self.cell(95, 5, "Minutes of Meeting")
        self.cell(95, 5, f"Page {self.page_no()}/{{nb}}", align="R")


_BODY_INDENT = 6


def _field(pdf: NotulenPDF, label: str, value: str, label_w: int = 48) -> None:
    """Renders 'Label : Value' the way the university template does, wrapping long values."""
    pdf.set_font(_FONT_FAMILY, "", 10)
    pdf.set_x(pdf.l_margin + _BODY_INDENT)
    pdf.cell(label_w, 6.5, label)
    pdf.multi_cell(0, 6.5, f": {value}", new_x="LMARGIN", new_y="NEXT")


def _section_heading(pdf: NotulenPDF, heading: str) -> None:
    """heading is passed pre-formatted, e.g. '1  PESERTA' (no period, matches template)."""
    pdf.set_font(_FONT_FAMILY, "B", 11)
    pdf.cell(0, 7, heading, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1.5)


def _wrap_cells(pdf: NotulenPDF, values: list[str], widths: list[int], line_h: int) -> list[list[str]]:
    return [
        pdf.multi_cell(w, line_h, str(text), dry_run=True, output=MethodReturnValue.LINES) or [""]
        for text, w in zip(values, widths)
    ]


def _draw_row(
    pdf: NotulenPDF,
    x_start: float,
    values: list[str],
    widths: list[int],
    aligns: list[str],
    line_h: int,
) -> None:
    """Draws one row at the current y position, plain black border (no fill) — no
    page-break handling."""
    wrapped = _wrap_cells(pdf, values, widths, line_h)
    row_h = max(len(lines) for lines in wrapped) * line_h
    y0 = pdf.get_y()
    x = x_start
    for lines, w, align in zip(wrapped, widths, aligns):
        pdf.rect(x, y0, w, row_h, style="D")
        pdf.set_xy(x, y0)
        pdf.multi_cell(w, line_h, "\n".join(lines), align=align, border=0)
        x += w
    pdf.set_xy(x_start, y0 + row_h)


def _table_row(
    pdf: NotulenPDF,
    x_start: float,
    values: list[str],
    widths: list[int],
    aligns: list[str] | None = None,
    line_h: int = 6,
    header: tuple[list[str], list[str], int, int] | None = None,
) -> None:
    """Draws one table row using the font already set by the caller. Long text wraps
    onto extra lines inside its own cell instead of overflowing into the next column;
    row height grows to fit whichever cell wrapped the most. If a page break happens
    mid-table, `header` — a (values, aligns, header_font_size, body_font_size) tuple —
    is redrawn first so the new page still shows column labels."""
    aligns = aligns or ["L"] * len(values)
    row_h = max(len(lines) for lines in _wrap_cells(pdf, values, widths, line_h)) * line_h

    if pdf.get_y() + row_h > pdf.page_break_trigger:
        pdf.add_page()
        if header is not None:
            h_values, h_aligns, h_size, body_size = header
            pdf.set_font(_FONT_FAMILY, "B", h_size)
            pdf.set_x(x_start)
            _draw_row(pdf, x_start, h_values, widths, h_aligns, line_h)
            pdf.set_font(_FONT_FAMILY, "", body_size)
            pdf.set_x(x_start)

    _draw_row(pdf, x_start, values, widths, aligns, line_h)


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
    pdf.add_font(_FONT_FAMILY, "", f"{_FONT_DIR}/DejaVuSerif.ttf")
    pdf.add_font(_FONT_FAMILY, "B", f"{_FONT_DIR}/DejaVuSerif-Bold.ttf")
    pdf.add_font(_FONT_FAMILY, "I", f"{_FONT_DIR}/DejaVuSerif-Italic.ttf")
    pdf.add_font(_FONT_FAMILY, "BI", f"{_FONT_DIR}/DejaVuSerif-BoldItalic.ttf")
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.header_title = meeting.title.upper()[:60]
    pdf.header_date = f"Tanggal Pertemuan {_fmt_date_slash(meeting.scheduled_at)}"

    # ── COVER PAGE ───────────────────────────────────────────────────────────
    pdf.add_page()

    logo_path = Path(settings.ORG_LOGO_PATH) if settings.ORG_LOGO_PATH else None
    has_logo = logo_path is not None and logo_path.is_file()
    if has_logo:
        y0 = pdf.get_y()
        pdf.image(str(logo_path), x=pdf.l_margin, y=y0, h=14)
        pdf.set_xy(pdf.l_margin, y0 + 3)
        pdf.set_font(_FONT_FAMILY, "B", 11)
        pdf.cell(0, 8, settings.ORG_NAME, align="R", new_x="LMARGIN", new_y="NEXT")
        pdf.set_y(y0 + 18)
    else:
        pdf.set_font(_FONT_FAMILY, "B", 12)
        pdf.cell(0, 14, settings.ORG_NAME, align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_line_width(0.8)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(22)

    pdf.set_font(_FONT_FAMILY, "BI", 18)
    pdf.multi_cell(0, 9, meeting.title.upper(), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    pdf.set_font(_FONT_FAMILY, "B", 13)
    pdf.cell(0, 8, "MINUTES OF MEETING", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)
    pdf.set_line_width(0.3)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(9)

    pdf.set_font(_FONT_FAMILY, "", 11)
    for line in (
        f"Tanggal Pertemuan: {_fmt_date_slash(meeting.scheduled_at)}",
        f"Lokasi Pertemuan: {meeting.location or '-'}",
        f"Diinisiasi oleh: {organizer_name}",
    ):
        pdf.cell(0, 7.5, line, align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_y(pdf.h - 25)
    pdf.set_line_width(0.8)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())

    # ── CONTENT PAGES ─────────────────────────────────────────────────────────
    pdf.add_page()

    # RINGKASAN (fitur Kioku, di luar format resmi kampus, ditaruh sebelum struktur bernomor)
    _section_heading(pdf, "RINGKASAN")
    pdf.set_font(_FONT_FAMILY, "", 10)
    pdf.set_x(pdf.l_margin + _BODY_INDENT)
    pdf.multi_cell(0, 6, summary.tldr or "-", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # 1 PESERTA
    _section_heading(pdf, "1.  PESERTA")

    peserta_widths = [10, 46, 34, 24, 24, 22, 20]
    peserta_aligns = ["C", "L", "L", "L", "L", "L", "C"]
    peserta_header_values = ["No", "Nama", "Jabatan", "Unit", "Telepon", "Status", "Paraf"]
    peserta_header = (peserta_header_values, peserta_aligns, 8.5, 8.5)
    table_x = pdf.l_margin + _BODY_INDENT

    pdf.set_line_width(0.15)
    pdf.set_font(_FONT_FAMILY, "B", 8.5)
    _table_row(pdf, table_x, peserta_header_values, peserta_widths, aligns=peserta_aligns, line_h=6.5)

    pdf.set_font(_FONT_FAMILY, "", 8.5)
    for i, p in enumerate(participants, start=1):
        name = p.user.name if p.user else p.email
        jabatan = p.user.job_title if (p.user and p.user.job_title) else "-"
        unit = p.user.department if (p.user and p.user.department) else "-"
        # Field nomor telepon belum ada di model User — begitu tersedia, baris ini
        # otomatis kepakai tanpa perlu ubah kode (kosong dulu, diisi manual dulu).
        phone = getattr(p.user, "phone", None) if p.user else None
        _table_row(
            pdf, table_x,
            [str(i), name, jabatan, unit, phone or "", _attendance_label(p), ""],
            peserta_widths, aligns=peserta_aligns, line_h=6.5, header=peserta_header,
        )

    pdf.ln(6)

    # 2 LOKASI PERTEMUAN
    _section_heading(pdf, "2.  LOKASI PERTEMUAN")
    _field(pdf, "Gedung", meeting.location_building or "-")
    _field(pdf, "Ruang", meeting.location_room or "-")
    _field(pdf, "Instansi", settings.ORG_NAME)
    _field(pdf, "Kabupaten/Kota", meeting.location_city or "-")
    pdf.ln(4)

    # 3 MULAI PERTEMUAN
    start_time = _fmt_time_wib(meeting.scheduled_at)
    _section_heading(pdf, "3.  MULAI PERTEMUAN")
    _field(pdf, "Rencana Awal", start_time)
    _field(pdf, "Aktual Pertemuan", start_time)
    _field(pdf, "Notulen", organizer_name)
    pdf.ln(4)

    # 4 AGENDA PERTEMUAN (data sama seperti "topik yang dibahas")
    topics = summary.topics or []
    _section_heading(pdf, "4.  AGENDA PERTEMUAN")
    pdf.set_font(_FONT_FAMILY, "", 10)
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
    _section_heading(pdf, "5.  SELESAI PERTEMUAN")
    _field(pdf, "Rencana Selesai", end_time)
    _field(pdf, "Aktual Selesai", end_time)
    pdf.ln(4)

    # 6 RENCANA AKSI PASCA PERTEMUAN (data sama seperti "action items")
    _section_heading(pdf, "6.  RENCANA AKSI PASCA PERTEMUAN")

    aksi_widths = [10, 82, 50, 40]
    aksi_aligns = ["C", "L", "L", "L"]
    aksi_header_values = ["No", "Aksi", "Ditugaskan ke-", "Batas Waktu"]
    aksi_header = (aksi_header_values, aksi_aligns, 9, 9)
    table_x = pdf.l_margin + _BODY_INDENT

    pdf.set_line_width(0.15)
    pdf.set_font(_FONT_FAMILY, "B", 9)
    _table_row(pdf, table_x, aksi_header_values, aksi_widths, aligns=aksi_aligns)

    pdf.set_font(_FONT_FAMILY, "", 9)
    if action_items:
        for i, ai in enumerate(action_items, start=1):
            pic = "-"
            if ai.assignee_participant and ai.assignee_participant.user:
                pic = ai.assignee_participant.user.name
            due = _fmt_date_short(ai.due_date)
            _table_row(
                pdf, table_x,
                [str(i), ai.task, pic, due],
                aksi_widths, aligns=aksi_aligns, header=aksi_header,
            )
    else:
        pdf.set_x(table_x)
        pdf.cell(0, 6, "-", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    # 7 KEPUTUSAN PERTEMUAN (data sama seperti "keputusan")
    decisions = summary.decisions or []
    _section_heading(pdf, "7.  KEPUTUSAN PERTEMUAN")
    pdf.set_font(_FONT_FAMILY, "", 10)
    if decisions:
        for idx, d in enumerate(decisions, start=1):
            pdf.set_x(pdf.l_margin + _BODY_INDENT)
            pdf.multi_cell(0, 6, f"{idx}. {d}", new_x="LMARGIN", new_y="NEXT")
    else:
        pdf.set_x(pdf.l_margin + _BODY_INDENT)
        pdf.cell(0, 6, "-", new_x="LMARGIN", new_y="NEXT")

    return bytes(pdf.output())