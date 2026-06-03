import smtplib
import uuid
import logging
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from sqlalchemy.orm import Session

from app.config import settings
from app.models.email_log import EmailLog, EmailType, EmailStatus

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
    summary_tldr: str,
    decisions: list[str],
    action_items: list[dict],
    meeting_id: uuid.UUID,
    db: Session,
) -> None:
    scheduled_str = scheduled_at.strftime("%d %B %Y %H:%M")

    decisions_html = "".join(f"<li>{d}</li>" for d in decisions) if decisions else "<li>-</li>"

    if action_items:
        rows = "".join(
            f"<tr><td>{item.get('task', '')}</td>"
            f"<td>{item.get('due_date') or '-'}</td></tr>"
            for item in action_items
        )
        action_items_html = (
            "<table border='1' cellpadding='4'>"
            "<thead><tr><th>Tugas</th><th>Tenggat</th></tr></thead>"
            f"<tbody>{rows}</tbody></table>"
        )
    else:
        action_items_html = "<p>Tidak ada action item untuk Anda.</p>"

    body_html = f"""<html><body>
<p>Yth. {recipient_name},</p>
<p>Berikut notulen rapat <b>{meeting_title}</b> pada {scheduled_str}.</p>
<h3>Ringkasan</h3>
<p>{summary_tldr}</p>
<h3>Keputusan</h3>
<ul>{decisions_html}</ul>
<h3>Action Item Anda</h3>
{action_items_html}
<p>Terima kasih.</p>
</body></html>"""

    status = EmailStatus.sent
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Notulen Rapat: {meeting_title}"
        msg["From"] = settings.SMTP_USER or "noreply@meetmate.local"
        msg["To"] = recipient_email
        msg.attach(MIMEText(body_html, "html"))

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
