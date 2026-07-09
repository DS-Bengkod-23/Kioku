# PR: Backend — Checkin Portal + PDF Notulen + QR Code

**Branch:** `backend`  
**Plan:** `plan/plan-checkin-portal.md`, `plan/plan-pdf-qr.md`

---

## Summary

- Tambah `duration_minutes` ke Meeting sebagai dasar attendance lock dinamis
- Refactor email notulen — dari kirim konten lengkap menjadi link portal + PDF attachment
- Embed QR code di email undangan (di samping link teks)
- Generate PDF Berita Acara otomatis dan expose endpoint download
- Fix 2 bug yang ditemukan saat review FE: `meeting_id` hilang dari response check-in + endpoint PDF portal butuh JWT

---

## Perubahan

### `duration_minutes` — attendance lock dinamis

- **`models/meeting.py`** — tambah field `duration_minutes: int` (default 60)
- **`alembic/versions/a1b2c3d4e5f6_...py`** — migration baru, `ADD COLUMN duration_minutes INTEGER NOT NULL DEFAULT 60`
- **`schemas/meeting.py`** — tambah `duration_minutes` ke `MeetingCreate`, `MeetingUpdate`, `MeetingDetail`
- **`services/meeting.py`** — teruskan `duration_minutes` saat buat meeting (sebelumnya field ini terlewat)
- **`services/checkin.py`** — `_is_attendance_locked()` kini pakai `scheduled_at + duration_minutes + 30 menit grace` sebagai fallback (sebelumnya hardcode 48 jam)
- **`services/recording.py`** — `attendance_locked_at` di-set ke `now()` saat recording diupload (sebelumnya `now() + 2 jam`)

### QR Code di email undangan

- **`services/qr.py`** *(file baru)* — `generate_qr_base64(url)` menggunakan `qrcode[pil]`, output base64 PNG
- **`services/email.py`** — `send_invitation_email()` embed QR code sebagai inline image `data:image/png;base64,...` di bawah link teks

### PDF Notulen

- **`services/pdf.py`** *(file baru)* — `generate_notulen_pdf()` menggunakan `fpdf2`, format Berita Acara: info rapat, tabel peserta + status hadir, ringkasan, keputusan, topik, action items
- **`services/email.py`** — `send_notulen_email()` direfactor: hapus parameter `summary_tldr/decisions/action_items`, ganti dengan `checkin_url` + `pdf_bytes`. Email body jadi notifikasi singkat + link portal. PDF dikirim sebagai attachment
- **`routers/meetings.py`** — endpoint baru `GET /meetings/{id}/notulen.pdf` (requires JWT), untuk download dari dashboard organizer/peserta
- **`routers/checkin.py`** — endpoint baru `GET /check-in/{token}/notulen.pdf` (public, no JWT), untuk download dari portal peserta
- **`tasks/process_recording.py`** — generate PDF satu kali setelah ML selesai, pass ke loop email. Loop sekarang skip peserta yang tidak punya invitation token (organizer)

### `requirements.txt`

Tambah:
```
qrcode[pil]==8.0
fpdf2==2.8.2
```

### Bugfix — response check-in

- **`schemas/checkin.py`** — tambah `meeting_id: uuid.UUID` ke `CheckinPageResponse` (dibutuhkan FE untuk tombol download PDF di portal)
- **`services/checkin.py`** — tambah `meeting_id=meeting.id` ke return `get_checkin_info()`

---

## Cara Menjalankan

### Full Docker
```bash
make build    # wajib — ada library baru di requirements.txt
make migrate  # apply migration duration_minutes
make up
```

### Hybrid (infrastruktur Docker, app lokal)
```bash
# 1. Jalankan infrastruktur
docker compose up -d postgres redis minio mailhog

# 2. Install library baru
cd backend
pip install -r requirements.txt

# 3. Apply migration
alembic upgrade head

# 4. Jalankan backend API
uvicorn app.main:app --reload --port 8000

# 5. Rebuild celery-worker (wajib — ada library baru)
cd ..
docker compose build celery-worker
docker compose up -d --no-deps celery-worker

# 6. Jalankan frontend (terminal baru)
cd frontend
npm run dev
```

---

## Test Plan

- [ ] Buat meeting dengan `duration_minutes=30` → cek field tersimpan di DB
- [ ] Buat meeting → cek Mailhog: email undangan berisi link teks + QR code image
- [ ] Buka magic link sebelum `scheduled_at + 30 menit + 30 grace` → tombol check-in aktif
- [ ] Buka magic link setelah window → tombol terkunci
- [ ] Upload recording → cek `attendance_locked_at = now()` di DB (bukan +2 jam)
- [ ] Setelah ML selesai → cek Mailhog: email notulen berisi link portal + PDF attachment (tanpa konten lengkap)
- [ ] Buka PDF attachment → verifikasi semua section ada (peserta, ringkasan, keputusan, action items)
- [ ] `GET /meetings/{id}/notulen.pdf` dengan JWT → file ter-download
- [ ] `GET /check-in/{token}/notulen.pdf` tanpa login → file ter-download
- [ ] `GET /meetings/{id}/notulen.pdf` sebelum ML selesai → 404 "Notulen belum tersedia"
