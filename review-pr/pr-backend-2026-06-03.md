# PR: feat(backend): complete backend API — auth, meetings, recordings, check-in, action items

## Summary

PR ini membangun seluruh layer backend MeetMate dari nol — struktur folder, database, semua endpoint REST, services, dan Celery worker untuk ML pipeline.

---

## Yang Dibangun

### Setup & Infrastruktur
- FastAPI app dengan CORS middleware (`main.py`, `config.py`, `database.py`)
- Celery worker instance terhubung ke Redis (`worker.py`)
- Alembic setup lengkap dengan initial migration (11 tabel, PostgreSQL enum-safe)
- MinIO integration via boto3 S3 client (`services/storage.py`)

### Endpoints (semua di bawah `/api/v1`)

| Method | Path | Deskripsi | Auth |
|--------|------|-----------|------|
| POST | `/auth/register` | Registrasi user baru | — |
| POST | `/auth/login` | Login, return JWT token | — |
| POST | `/meetings/` | Buat rapat + undang peserta + kirim email | ✅ |
| GET | `/meetings/` | List rapat milik user (paginated, filter status) | ✅ |
| GET | `/meetings/search` | Search rapat by keyword | ✅ |
| GET | `/meetings/{id}` | Detail rapat lengkap | ✅ |
| PATCH | `/meetings/{id}` | Update rapat (organizer only) | ✅ |
| DELETE | `/meetings/{id}` | Hapus rapat (organizer only) | ✅ |
| POST | `/meetings/{id}/recording` | Upload audio → MinIO → dispatch Celery task | ✅ |
| GET | `/meetings/{id}/recording/status` | Polling status ML pipeline | ✅ |
| DELETE | `/meetings/{id}/recording` | Hapus recording | ✅ |
| GET | `/check-in/{token}` | Halaman check-in publik | — |
| POST | `/check-in/{token}/confirm` | Konfirmasi kehadiran via magic-link | — |
| PATCH | `/meetings/{id}/participants/{pid}/attendance` | Update absensi manual (organizer) | ✅ |
| PATCH | `/action-items/{id}` | Update status action item (assignee) | ✅ |
| GET | `/me/action-items` | List action item milik user sendiri | ✅ |

### Services & Business Logic
- **Auth** — JWT + bcrypt, `get_current_user` dependency
- **Meeting** — create dengan auto-generate invitation token per peserta, search, soft-delete guard
- **Recording** — async upload ke MinIO, enqueue Celery task `process_recording`
- **Check-in** — validasi token magic-link, single-use, expire 24h setelah meeting berakhir
- **Email** — kirim undangan + notulen via SMTP (Mailhog di dev)
- **Pipeline task** — orkestrasi penuh: `transcribe → diarize → merge → summarize → action_items → email`

### Models (SQLAlchemy ORM)
`User`, `Meeting`, `MeetingParticipant`, `Invitation`, `Recording`, `Transcript`, `Summary`, `ActionItem`, `Attendance`, `EmailLog`

---

## Test Plan

- [ ] `docker compose up -d` → semua service naik (Postgres, Redis, MinIO, Mailhog)
- [ ] `alembic upgrade head` → migrasi berhasil tanpa error `DuplicateObject`
- [ ] `POST /auth/register` + `POST /auth/login` → dapat JWT token
- [ ] `POST /meetings/` → rapat terbuat, email undangan muncul di Mailhog (`localhost:8025`)
- [ ] `POST /meetings/{id}/recording` → file tersimpan di MinIO bucket, Celery task ter-enqueue
- [ ] `GET /meetings/{id}/recording/status` → status berubah sesuai progress pipeline
- [ ] `GET /check-in/{token}` → halaman check-in accessible tanpa login
- [ ] `POST /check-in/{token}/confirm` → status absensi ter-update ke `hadir`
- [ ] Swagger docs terbuka di `http://localhost:8000/docs`

---

## Notes untuk Reviewer

> **Koordinasi ML (Azmi):** Function signatures di `tasks/process_recording.py` sudah sesuai kontrak di `CLAUDE.md` — jangan ubah tanpa koordinasi lintas tim.

> **Koordinasi Frontend (Helena):** Semua response shape sudah sesuai `docs/API_CONTRACT.md`. Pastikan `NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1` di `.env.local`.

> **Untuk prod:** Ganti MinIO dengan Cloudflare R2 cukup lewat env vars saja — kode tidak perlu diubah karena pakai boto3 S3-compatible interface.
