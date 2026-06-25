# Plan: PDF Notulen + QR Code Check-in

**Status:** READY TO IMPLEMENT  
**Owner:** BE (Audi) + FE (Helena) | ML: tidak ada perubahan

---

## Context

Dua fitur untuk meningkatkan experience pengguna non-teknis:

1. **PDF Notulen** — setelah ML selesai, generate PDF "Berita Acara" resmi, kirim sebagai lampiran email, dan bisa didownload dari dashboard
2. **QR Code Check-in** — magic link per peserta di-embed sebagai QR code di email undangan *di samping link teks yang bisa diklik*, sehingga peserta bebas memilih: tap link (buka di HP) atau scan QR (buka dari device lain / kertas cetak)

---

## QR Code Check-in

### Keputusan desain

Email undangan selalu berisi **dua hal sekaligus**:
- Link teks yang bisa diklik — untuk yang buka email di HP
- QR code image di bawahnya — untuk yang scan dari device lain atau mau cetak

```
Konfirmasi kehadiran Anda melalui tautan berikut:
→ https://meetmate.com/check-in/abc123...

Atau scan QR code berikut:
[gambar QR 200x200]
```

QR code bukan pengganti magic link — keduanya encode URL yang sama, peserta pilih yang lebih mudah.

### Backend — Audi

#### 1. Tambah library ke `backend/requirements.txt`
```
qrcode[pil]
```

#### 2. Buat `backend/app/services/qr.py` (file baru)
```python
import qrcode
import io
import base64

def generate_qr_base64(url: str) -> str:
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()
```

#### 3. Update `backend/app/services/email.py` — `send_invitation_email()`
Embed QR code sebagai inline base64 image di samping link teks:
```python
from app.services.qr import generate_qr_base64

def send_invitation_email(...):
    checkin_url = f"{settings.APP_BASE_URL}/check-in/{checkin_token}"
    qr_b64 = generate_qr_base64(checkin_url)

    body_html = f"""<html><body>
<p>Yth. {recipient_name},</p>
<p>Anda diundang ke rapat <b>{meeting_title}</b> pada {scheduled_str} di {location_str}.</p>

<p>Konfirmasi kehadiran melalui tautan berikut:<br>
<a href="{checkin_url}">{checkin_url}</a></p>

<p>Atau scan QR code berikut:</p>
<img src="data:image/png;base64,{qr_b64}" width="200" height="200" alt="QR Check-in"/>

<p>Terima kasih.</p>
</body></html>"""
```
QR di-embed sebagai base64 inline — tidak butuh penyimpanan file eksternal, langsung tampil di email.

### Frontend — Helena

Tidak ada perubahan frontend untuk fitur QR. QR hanya ada di email, bukan di UI web.

---

## PDF Notulen

### Konten PDF (format Berita Acara)

```
═══════════════════════════════════════════
            NOTULEN RAPAT
               MeetMate
═══════════════════════════════════════════

Judul     : Review Sprint Q2
Tanggal   : Jumat, 20 Juni 2026, 09:00
Lokasi    : Ruang Rapat Lantai 3
Dipimpin  : Budi Santoso

───────────────────────────────────────────
PESERTA
───────────────────────────────────────────
No   Nama                Status
1.   Budi Santoso        Hadir
2.   Siti Rahayu         Hadir
3.   Reza Firmansyah     Tidak Hadir

───────────────────────────────────────────
RINGKASAN
───────────────────────────────────────────
[summary.tldr]

───────────────────────────────────────────
KEPUTUSAN
───────────────────────────────────────────
1. [decisions[0]]
2. [decisions[1]]

───────────────────────────────────────────
TOPIK YANG DIBAHAS
───────────────────────────────────────────
• [topics[0]]
• [topics[1]]

───────────────────────────────────────────
ACTION ITEMS
───────────────────────────────────────────
No   Tugas                     PIC     Tenggat
1.   Selesaikan laporan Q2     Siti    27 Jun 2026
2.   Buat proposal budget      Reza    30 Jun 2026

───────────────────────────────────────────
Dibuat otomatis oleh MeetMate · [timestamp]
═══════════════════════════════════════════
```

### Backend — Audi

#### 1. Tambah library ke `backend/requirements.txt`
```
fpdf2
```
`fpdf2` — pure Python, tidak ada dependensi sistem, aman untuk Docker.

#### 2. Buat `backend/app/services/pdf.py` (file baru)
```python
from fpdf import FPDF
from app.models.meeting import Meeting
from app.models.summary import Summary
from app.models.action_item import ActionItem
from app.models.participant import MeetingParticipant

def generate_notulen_pdf(
    meeting: Meeting,
    organizer_name: str,
    participants: list[MeetingParticipant],  # attendance sudah di-load
    summary: Summary,
    action_items: list[ActionItem],
) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    # ... build layout sesuai format Berita Acara di atas
    return pdf.output()
```

#### 3. Endpoint baru di `backend/app/routers/meetings.py`
```python
from fastapi.responses import Response

@router.get("/meetings/{meeting_id}/notulen.pdf")
def download_notulen_pdf(
    meeting_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verifikasi current_user adalah peserta atau organizer meeting ini
    # Query meeting, summary, action_items, participants + attendance
    # Kalau summary belum ada (ML belum selesai) → 404 "Notulen belum tersedia"
    pdf_bytes = generate_notulen_pdf(...)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="notulen-{meeting_id}.pdf"'},
    )
```

#### 4. Update `backend/app/services/email.py` — `send_notulen_email()`
Tambah parameter `pdf_bytes: bytes`, attach ke email sebagai lampiran:
```python
from email import encoders
from email.mime.base import MIMEBase

def send_notulen_email(
    recipient_email: str,
    recipient_name: str,
    meeting_title: str,
    scheduled_at: datetime,
    checkin_url: str,
    pdf_bytes: bytes,          # ← tambah
    meeting_id: UUID,
    db: Session,
) -> None:
    msg = MIMEMultipart("mixed")  # "mixed" agar bisa attach file
    
    # Body: notifikasi singkat + link portal
    body = MIMEText(f"""...<a href="{checkin_url}">Buka Portal Saya</a>...""", "html")
    msg.attach(body)
    
    # Attachment: PDF
    att = MIMEBase("application", "octet-stream")
    att.set_payload(pdf_bytes)
    encoders.encode_base64(att)
    att.add_header("Content-Disposition", f'attachment; filename="notulen-{meeting_title}.pdf"')
    msg.attach(att)
```

#### 5. Update `backend/app/tasks/process_recording.py`
Generate PDF satu kali setelah semua data tersimpan, lalu pass ke setiap email:
```python
from app.services.pdf import generate_notulen_pdf

# Generate PDF satu kali (sama untuk semua peserta)
pdf_bytes = generate_notulen_pdf(
    meeting=meeting,
    organizer_name=...,
    participants=participants,
    summary=summary_obj,
    action_items=db_action_items,
)

for p in participants:
    checkin_url = f"{settings.APP_BASE_URL}/check-in/{p.invitation.token}"
    send_notulen_email(
        ...,
        checkin_url=checkin_url,
        pdf_bytes=pdf_bytes,
        ...,
    )
```

### Frontend — Helena

#### 1. Meeting detail page — tombol download PDF
Tambah tombol "Download Notulen PDF" yang muncul hanya ketika `processing_status = completed`:

```typescript
const downloadPdf = async () => {
  const res = await api.get(`/meetings/${meetingId}/notulen.pdf`, {
    responseType: "blob",
  });
  const url = URL.createObjectURL(res.data);
  const a = document.createElement("a");
  a.href = url;
  a.download = `notulen-${meetingTitle}.pdf`;
  a.click();
  URL.revokeObjectURL(url);
};
```
Pakai `fetch` + `blob` (bukan `<a href>` langsung) karena endpoint butuh JWT header.

#### 2. Portal check-in peserta — tombol download PDF
Di kartu Notulen (section 2), setelah summary tampil, tambah tombol:
```
[Download Notulen PDF ↓]
```
Endpoint sama: `GET /meetings/:id/meeting_id/notulen.pdf`.  
Untuk portal (tanpa JWT), bisa tambahkan verifikasi via token check-in:
```
GET /check-in/{token}/notulen.pdf   ← alternatif endpoint khusus portal
```
Atau cukup tampilkan tombol yang redirect ke halaman login jika belum login.

---

## Urutan Implementasi

**Backend (Audi) — berurutan:**
1. Tambah `qrcode[pil]` dan `fpdf2` ke `requirements.txt`, rebuild image
2. Buat `services/qr.py` + update `send_invitation_email()` — QR di email undangan
3. Buat `services/pdf.py` — fungsi `generate_notulen_pdf()`
4. Tambah endpoint `GET /meetings/:id/notulen.pdf` di router meetings
5. Update `send_notulen_email()` — tambah parameter `pdf_bytes` + attach
6. Update `tasks/process_recording.py` — generate PDF lalu pass ke loop email

**Frontend (Helena) — bisa paralel setelah BE nomor 3–4 selesai:**
1. Meeting detail page — tombol download PDF (dengan fetch + blob)
2. Portal check-in — tombol download PDF di kartu Notulen

---

## Verifikasi End-to-End

**QR Code:**
1. Buat meeting → cek email di Mailhog → email berisi link teks + QR code image
2. Klik link teks → portal check-in terbuka ✓
3. Scan QR dari kamera HP → URL yang sama, portal terbuka di mobile browser ✓

**PDF Notulen:**
1. Upload recording → tunggu ML selesai → cek Mailhog
2. Email berisi: body singkat + link portal + lampiran PDF
3. Buka PDF → verifikasi semua section: info rapat, peserta + status, ringkasan, keputusan, action items
4. Klik "Download Notulen PDF" di dashboard → file terdownload `notulen-[judul].pdf`
5. Tombol download tidak muncul sebelum `processing_status = completed`
