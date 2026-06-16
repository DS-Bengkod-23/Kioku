# MeetMate Backend

FastAPI + Celery backend untuk MeetMate.

**Owner:** Audi

---

## Stack

- **FastAPI** - API layer
- **Celery + Redis** - background job processing
- **PostgreSQL** - database utama
- **Alembic** - database migration
- **MinIO** - file storage (via boto3)
- **SMTP / Mailhog** - email dispatch

---

## Struktur Folder

```
backend/
├── app/
│   ├── main.py              # entry point FastAPI
│   ├── config.py            # load .env settings
│   ├── database.py          # koneksi PostgreSQL
│   ├── worker.py            # Celery app instance
│   ├── routers/
│   │   ├── auth.py
│   │   ├── meetings.py
│   │   ├── recordings.py
│   │   ├── action_items.py
│   │   └── checkin.py
│   ├── models/              # SQLAlchemy models (tabel DB)
│   │   ├── user.py
│   │   ├── meeting.py
│   │   ├── participant.py
│   │   ├── attendance.py
│   │   ├── invitation.py
│   │   ├── recording.py
│   │   ├── transcript.py
│   │   ├── summary.py
│   │   ├── action_item.py
│   │   └── email_log.py
│   ├── schemas/             # Pydantic schemas (request/response)
│   │   ├── auth.py
│   │   ├── meeting.py
│   │   ├── recording.py
│   │   ├── action_item.py
│   │   └── checkin.py
│   ├── services/            # business logic
│   │   ├── auth.py
│   │   ├── meeting.py
│   │   ├── recording.py
│   │   ├── action_item.py
│   │   ├── invitation.py
│   │   ├── checkin.py
│   │   ├── storage.py       # upload/download MinIO
│   │   └── email.py         # kirim email via SMTP
│   └── tasks/
│       └── process_recording.py  # Celery task utama
├── alembic/                 # migration files
├── alembic.ini
├── requirements.txt
└── README.md
```

---

## Setup

**1. Install dependency**
```bash
pip install -r requirements.txt
```

**2. Pastikan infra jalan**
```bash
# Dari root repo
docker compose up -d
```

**3. Run migration**
```bash
alembic upgrade head
```

**4. Jalankan API**
```bash
uvicorn app.main:app --reload --port 8000
```

**5. Jalankan Celery Worker** (terminal terpisah, dari root project)

*Windows:*
```cmd
scripts\start-worker.bat
```

*Mac / Linux:*
```bash
./scripts/start-worker.sh
```

Atau manual (dari folder `backend/`):
```bash
# Windows: tambah --pool=solo karena Windows tidak support fork()
python -m celery -A app.worker worker --loglevel=info --pool=solo
```

---

## API Docs

Setelah API jalan, buka:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

Lihat juga `docs/API_CONTRACT.md` untuk detail request/response.

---

## Environment Variables

Lihat `.env.example` di root repo. Copy ke `.env` sebelum run.

---

## Membuat Migration Baru

```bash
alembic revision --autogenerate -m "deskripsi perubahan"
alembic upgrade head
```