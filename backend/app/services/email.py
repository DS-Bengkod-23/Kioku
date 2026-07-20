import smtplib
import uuid
import logging
from datetime import date, datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from sqlalchemy.orm import Session

from app.config import settings
from app.models.email_log import EmailLog, EmailType, EmailStatus
from app.services.qr import generate_qr_bytes

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
    qr_bytes = generate_qr_bytes(checkin_url)

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
<p>Atau scan QR code yang terlampir pada email ini.</p>
<p>Terima kasih.</p>
</body></html>"""

    status = EmailStatus.sent
    try:
        msg = MIMEMultipart("mixed")
        msg["Subject"] = f"Undangan Rapat: {meeting_title}"
        msg["From"] = settings.SMTP_USER or "noreply@kioku.local"
        msg["To"] = recipient_email

        msg.attach(MIMEText(body_html, "html"))

        qr_img = MIMEImage(qr_bytes, "png")
        qr_img.add_header("Content-Disposition", 'attachment; filename="qr-checkin.png"')
        msg.attach(qr_img)

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
    # Sengaja tidak commit di sini — lihat catatan di create_invitations().
    # Caller (create_meeting/update_meeting) yang commit di akhir transaksinya.


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
        msg["From"] = settings.SMTP_USER or "noreply@kioku.local"
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
    # Sengaja tidak commit di sini — caller (process_recording_task) commit setelah
    # semua peserta selesai dikirimi, sekaligus dengan attendance_locked/status.


def send_password_reset_email(recipient_email: str, recipient_name: str, reset_token: str) -> None:
    # Sengaja tidak menelan exception, sama seperti send_action_item_reminder_email:
    # caller (trigger_password_reset) harus tahu kalau pengiriman gagal, bukan diam-diam
    # melaporkan sukses padahal user gak pernah dapat link reset-nya.
    reset_url = f"{settings.APP_BASE_URL}/reset-password/{reset_token}"

    body_html = f"""<html><body>
<p>Yth. {recipient_name},</p>
<p>Admin telah memicu reset password untuk akun Anda. Klik tautan berikut untuk membuat password baru sendiri
— tautan ini cuma berlaku 30 menit dan cuma bisa dipakai sekali:</p>
<p><a href="{reset_url}" style="font-size:16px;font-weight:bold;">Reset Password Saya &rarr;</a></p>
<p>Kalau Anda tidak meminta ini, abaikan email ini — password Anda tidak akan berubah kecuali Anda membuka
tautan di atas.</p>
<p>Terima kasih.</p>
</body></html>"""

    msg = MIMEMultipart("mixed")
    msg["Subject"] = "Reset Password Akun Kioku Anda"
    msg["From"] = settings.SMTP_USER or "noreply@kioku.local"
    msg["To"] = recipient_email
    msg.attach(MIMEText(body_html, "html"))

    with _smtp_connection() as conn:
        conn.sendmail(msg["From"], [recipient_email], msg.as_string())


def send_action_item_reminder_email(
    recipient_email: str,
    recipient_name: str,
    task: str,
    due_date: date,
    meeting_title: str,
    action_url: str,
) -> None:
    # Sengaja tidak menelan exception (beda dari send_invitation_email/send_notulen_email
    # di atas) -- caller (tasks/action_item_reminders.py) memakai kegagalan ini untuk
    # memutuskan TIDAK mengisi reminder_sent_at, supaya item tetap dicoba lagi di run
    # harian berikutnya alih-alih diam-diam ditandai terkirim padahal gagal.
    due_str = due_date.strftime("%d %B %Y")

    body_html = f"""<html><body>
<p>Yth. {recipient_name},</p>
<p>Ini pengingat bahwa tugas berikut jatuh tempo <b>besok, {due_str}</b>:</p>
<ul>
  <li><b>Tugas:</b> {task}</li>
  <li><b>Rapat:</b> {meeting_title}</li>
</ul>
<p><a href="{action_url}" style="font-size:16px;font-weight:bold;">Buka &rarr;</a></p>
<p>Terima kasih.</p>
</body></html>"""

    msg = MIMEMultipart("mixed")
    msg["Subject"] = f"Pengingat: Tugas Anda jatuh tempo besok - {task}"
    msg["From"] = settings.SMTP_USER or "noreply@kioku.local"
    msg["To"] = recipient_email
    msg.attach(MIMEText(body_html, "html"))

    with _smtp_connection() as conn:
        conn.sendmail(msg["From"], [recipient_email], msg.as_string())
