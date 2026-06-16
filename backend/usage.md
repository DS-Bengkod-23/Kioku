# Backend Usage Guide

Panduan setup, menjalankan, dan memverifikasi backend MeetMate berjalan dengan benar.

---

## Prasyarat

| Kebutuhan | Versi minimum | Cek |
|---|---|---|
| Python | 3.11+ | `python --version` |
| Docker Desktop | terbaru | `docker --version` |
| Docker Compose | terbaru | `docker compose version` |

> **Catatan Python 3.14:** `psycopg2-binary` belum punya wheel untuk Python 3.14. Project ini sudah diganti ke `psycopg[binary]` (psycopg3) — tidak perlu action apapun, ini sudah tercatat di `requirements.txt`.

---

## Setup (satu kali)

### 1. Pastikan file `.env` ada di root repo

File `.env` ada di `MeetMate/Aplikasi/.env` (bukan di dalam folder `backend/`). Backend membaca env dari sana otomatis.

Kalau belum ada, copy dari contoh:
```bash
# dari root repo
cp .env.example .env
```

Untuk dev lokal, nilai default di `.env.example` sudah langsung bisa dipakai tanpa perlu diubah.

---

### 2. Jalankan infrastruktur (Docker)

Dari **root repo** (`MeetMate/Aplikasi/`):
```bash
docker compose up -d postgres redis minio mailhog
```

Ini menjalankan:
| Container | Port | Fungsi |
|---|---|---|
| `meetmate_postgres` | 5432 | Database utama |
| `meetmate_redis` | 6379 | Celery broker |
| `meetmate_minio` | 9000 / 9001 | File storage |
| `meetmate_mailhog` | 1025 / 8025 | SMTP dev (lihat email di browser) |

Tunggu sampai semua container `healthy`:
```bash
docker compose ps
```

---

### 3. Install dependency Python

Dari folder `backend/`:
```bash
cd backend
pip install -r requirements.txt
```

---

### 4. Jalankan database migration

```bash
# masih di folder backend/
python -m alembic upgrade head
```

Perintah ini membuat semua tabel dan enum di PostgreSQL. Output yang diharapkan:
```
INFO  [alembic.runtime.migration] Running upgrade  -> 9a7befed844a, initial schema
```

---

## Menjalankan Backend (sehari-hari)

Setiap kali mau development, urutan yang benar:

**Terminal 1 — pastikan Docker jalan:**
```bash
docker compose up -d
```

**Terminal 2 — API server:**
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

**Terminal 3 — Celery worker** (dibutuhkan untuk proses recording):

*Cara paling mudah — dari root project:*
```cmd
scripts\start-worker.bat   # Windows
./scripts/start-worker.sh  # Mac/Linux
```

*Atau manual dari folder `backend/`:*
```bash
# Tambah --pool=solo di Windows karena tidak support fork()
python -m celery -A app.worker worker --loglevel=info --pool=solo
```

> `celery` dan `alembic` mungkin tidak ada di PATH secara langsung. Selalu pakai `python -m celery` dan `python -m alembic` untuk menghindari masalah ini.

---

## Verifikasi Backend Berjalan

### 1. Health check — API up

```bash
curl http://localhost:8000/health
```

Response yang diharapkan:
```json
{"status": "ok", "env": "development"}
```

Atau buka di browser: [http://localhost:8000/health](http://localhost:8000/health)

---

### 2. Swagger UI — dokumentasi interaktif

Buka di browser:
- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

Kalau halaman terbuka dan ada endpoint `/health` terdaftar, berarti FastAPI berjalan dengan benar.

---

### 3. Verifikasi koneksi database

```bash
cd backend
python -c "
from app.database import engine
with engine.connect() as conn:
    result = conn.execute(__import__('sqlalchemy').text('SELECT 1'))
    print('DB connection: OK')
"
```

---

### 4. Verifikasi tabel sudah dibuat

```bash
cd backend
python -c "
from app.database import engine
import sqlalchemy as sa
inspector = sa.inspect(engine)
tables = inspector.get_table_names()
print('Tables:', tables)
"
```

Output yang diharapkan (urutan boleh beda):
```
Tables: ['users', 'meetings', 'meeting_participants', 'invitations', 'attendances', 'recordings', 'transcripts', 'summaries', 'action_items', 'email_logs']
```

---

### 5. Verifikasi migration history

```bash
cd backend
python -m alembic history
python -m alembic current
```

`alembic current` harus menunjukkan revision `9a7befed844a (head)`.

---

### 6. Verifikasi import semua module

```bash
cd backend
python -c "
from app.main import app
from app.models import User, Meeting, MeetingParticipant, Invitation, Attendance, Recording, Transcript, Summary, ActionItem, EmailLog
from app.config import settings
print('All imports: OK')
print(f'APP_ENV: {settings.APP_ENV}')
print(f'DB: {settings.DATABASE_URL[:30]}...')
"
```

---

## Cek Layanan Pendukung

### PostgreSQL
```bash
docker exec meetmate_postgres pg_isready -U meetmate
```
Output: `localhost:5432 - accepting connections`

### Redis
```bash
docker exec meetmate_redis redis-cli ping
```
Output: `PONG`

### MinIO
Buka [http://localhost:9001](http://localhost:9001) — login dengan `minioadmin` / `minioadmin`.

### Mailhog (email dev)
Buka [http://localhost:8025](http://localhost:8025) — semua email yang dikirim backend akan muncul di sini.

---

## Troubleshooting

### Error: `connection refused` saat migration
Docker belum jalan atau belum healthy.
```bash
docker compose up -d
docker compose ps  # tunggu sampai semua "healthy"
```

### Error: `9 validation errors for Settings`
File `.env` tidak ditemukan. Pastikan file `.env` ada di **root repo** (`MeetMate/Aplikasi/.env`), bukan di dalam `backend/`.

### Error: `target database is not up to date`
Ada migration baru yang belum diapply.
```bash
python -m alembic upgrade head
```

### Error: `ModuleNotFoundError` saat jalankan `uvicorn` atau `celery`
Pastikan menjalankan dari folder `backend/` dan dependency sudah terinstall:
```bash
cd backend
pip install -r requirements.txt
```

### Port 8000 sudah dipakai
```bash
# cek proses yang pakai port 8000
netstat -ano | findstr :8000   # Windows
lsof -i :8000                  # Mac/Linux
```

### Membuat migration baru (setelah ubah model)
```bash
cd backend
python -m alembic revision --autogenerate -m "deskripsi perubahan"
python -m alembic upgrade head
```

---

## Ringkasan Perintah Harian

```bash
# 1. start infra saja (postgres, redis, minio, mailhog)
docker compose up -d postgres redis minio mailhog

# 2. API server
cd backend && uvicorn app.main:app --reload --port 8000

# 3. Celery worker (terminal terpisah, dari root project)
# Windows:
scripts\start-worker.bat
# Mac/Linux:
./scripts/start-worker.sh

# 4. cek semua OK
curl http://localhost:8000/health
```
