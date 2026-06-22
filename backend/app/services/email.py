import smtplib
import uuid
import logging
from datetime import datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from sqlalchemy.orm import Session

from app.config import settings
from app.models.email_log import EmailLog, EmailType, EmailStatus
from app.services.qr import generate_qr_base64

logger = logging.getLogger(__name__)


def _smtp_connection():
    if settings.SMTP_USE_TLS:
        conn = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT)
    else:
        conn = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
    if settings.SMTP_USER and settings.SMTP_PASSWORD:
        conn.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
    return conn


def send_invitation_email(
    recipient_email: str,
    recipient_name: str,
    meeting_title: str,
    scheduled_at: datetime,
    location: str,
    checkin_token: str,
    meeting_id: uuid.UUID,
    db: Session,
) -> None:
    checkin_url = f"{settings.APP_BASE_URL}/check-in/{checkin_token}"
    scheduled_str = scheduled_at.strftime("%d %B %Y %H:%M")
    location_str = location or "-"
    qr_b64 = generate_qr_base64(checkin_url)

    body_html = f"""<html><body>
<p>Yth. {recipient_name},</p>
<p>Anda diundang untuk menghadiri rapat berikut:</p>
<ul>
  <li><b>Judul:</b> {meeting_title}</li>
  <li><b>Waktu:</b> {scheduled_str}</li>
  <li><b>Lokasi:</b> {location_str}</li>
</ul>
<p>Konfirmasi kehadiran Anda melalui tautan berikut:<br>
<a href="{checkin_url}">{checkin_url}</a></p>
<p>Atau scan QR code berikut:</p>
<img src="data:image/png;base64,{qr_b64}" width="200" height="200" alt="QR Check-in"/>
<p>Terima kasih.</p>
</body></html>"""

    status = EmailStatus.sent
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Undangan Rapat: {meeting_title}"
        msg["From"] = settings.SMTP_USER or "noreply@meetmate.local"
        msg["To"] = recipient_email
        msg.attach(MIMEText(body_html, "html"))

        with _smtp_connection() as conn:
            conn.sendmail(msg["From"], [recipient_email], msg.as_string())
    except Exception:
        logger.exception("Failed to send invitation email to %s", recipient_email)
        status = EmailStatus.failed

    log = EmailLog(
        recipient=recipient_email,
        type=EmailType.invitation,
        meeting_id=meeting_id,
        status=status,
    )
    db.add(log)
    db.commit()


def send_notulen_email(
    recipient_email: str,
    recipient_name: str,
    meeting_title: str,
    scheduled_at: datetime,
    checkin_url: str,
    pdf_bytes: bytes,
    meeting_id: uuid.UUID,
    db: Session,
) -> None:
    scheduled_str = scheduled_at.strftime("%d %B %Y %H:%M")

    body_html = f"""<html><body>
<p>Yth. {recipient_name},</p>
<p>Rapat <b>{meeting_title}</b> pada {scheduled_str} telah selesai diproses.</p>
<p>Notulen lengkap (ringkasan, keputusan, dan action item Anda) tersedia di portal peserta:</p>
<p><a href="{checkin_url}" style="font-size:16px;font-weight:bold;">Buka Portal Saya &rarr;</a></p>
<p>Notulen PDF terlampir pada email ini.</p>
<p>Terima kasih.</p>
</body></html>"""

    safe_title = "".join(c if c.isalnum() or c in " _-" else "_" for c in meeting_title)

    status = EmailStatus.sent
    try:
        msg = MIMEMultipart("mixed")
        msg["Subject"] = f"Notulen Rapat: {meeting_title}"
        msg["From"] = settings.SMTP_USER or "noreply@meetmate.local"
        msg["To"] = recipient_email

        msg.attach(MIMEText(body_html, "html"))

        att = MIMEBase("application", "octet-stream")
        att.set_payload(pdf_bytes)
        encoders.encode_base64(att)
        att.add_header("Content-Disposition", f'attachment; filename="notulen-{safe_title}.pdf"')
        msg.attach(att)

        with _smtp_connection() as conn:
            conn.sendmail(msg["From"], [recipient_email], msg.as_string())
    except Exception:
        logger.exception("Failed to send notulen email to %s", recipient_email)
        status = EmailStatus.failed

    log = EmailLog(
        recipient=recipient_email,
        type=EmailType.distribution,
        meeting_id=meeting_id,
        status=status,
    )
    db.add(log)
    db.commit()
