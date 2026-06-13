# Perubahan Integrasi Docker

Dokumen ini mencatat semua perubahan yang dilakukan saat mengintegrasikan FE, BE, dan ML ke dalam satu Docker workflow.

---

## File Baru

### Dockerfiles
| File | Keterangan |
|---|---|
| `backend/Dockerfile.api` | Image untuk Backend API (FastAPI + uvicorn, port 8000) |
| `backend/Dockerfile.worker` | Image untuk Celery Worker — menggabungkan backend + ML dalam satu container, set `PYTHONPATH` otomatis agar bisa import keduanya |
| `frontend/Dockerfile` | Image untuk Frontend Next.js (multi-stage build: deps → build → runner) |

### Docker Support
| File | Keterangan |
|---|---|
| `backend/.dockerignore` | File yang dikecualikan dari build image backend. Awalnya salah mengecualikan `alembic.ini` (sudah diperbaiki) |
| `frontend/.dockerignore` | File yang dikecualikan dari build image frontend |

### Workflow & Tooling
| File | Keterangan |
|---|---|
| `Makefile` | Shortcut command: `make up`, `make down`, `make build`, `make migrate`, `make logs-api`, `make logs-worker` |
| `make.bat` | Versi Windows dari Makefile untuk yang tidak punya `make` |
| `.pre-commit-config.yaml` | Auto-format kode Python (ruff) dan JS sebelum `git commit`. Opsional, aktifkan dengan `pip install pre-commit && pre-commit install` |
| `docs/DOCKER_WORKFLOW.md` | Panduan lengkap cara pakai Docker workflow |

---

## File yang Dimodifikasi

### `docker-compose.yml`
**Sebelum:** hanya berisi 4 service infra (postgres, redis, minio, mailhog).

**Sesudah:** ditambahkan:
- **`frontend`** — Next.js di port 3000
- **`backend-api`** — FastAPI di port 8000, dengan environment override untuk koneksi antar container
- **`celery-worker`** — Celery + ML pipeline, environment override untuk koneksi antar container
- **`adminer`** — UI database viewer di port 8080

Environment override yang ditambahkan untuk `backend-api` dan `celery-worker` (agar koneksi antar container pakai nama service, bukan `localhost`):
```yaml
environment:
  - DATABASE_URL=postgresql://meetmate:meetmate@postgres:5432/meetmate
  - REDIS_URL=redis://redis:6379
  - MINIO_ENDPOINT=minio:9000
  - SMTP_HOST=mailhog
```

### `backend/app/config.py`
**Sebelum:** `Settings` tidak kenal field `LLM_PROVIDER`, `OPENAI_API_KEY`, `OPENAI_MODEL`, `HF_TOKEN` — menyebabkan error `Extra inputs are not permitted` saat startup.

**Sesudah:** ditambahkan field berikut ke class `Settings`:
```python
LLM_PROVIDER: str = "openai"
OPENAI_API_KEY: str = ""
OPENAI_MODEL: str = "gpt-4o-mini"
HF_TOKEN: str = ""
```

### `ml/requirements.txt`
**Sebelum:** `torch` dan `torchaudio` tanpa spesifikasi — pip download versi CUDA (500MB+) meski tidak ada GPU.

**Sesudah:** ditambahkan index URL PyTorch CPU-only:
```
--extra-index-url https://download.pytorch.org/whl/cpu
```

### `backend/Dockerfile.worker`
**Sesudah:** ditambahkan flag CPU-only saat install ML requirements:
```dockerfile
RUN pip install --no-cache-dir -r ml_requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu
```

### `backend/.dockerignore`
**Sebelum:** `alembic.ini` masuk daftar ignore — menyebabkan `make migrate` error "No script_location key found".

**Sesudah:** `alembic.ini` dihapus dari daftar ignore agar ter-copy ke dalam container.

### `ml/extract.py`
**Sebelum:** hardcode pakai OpenAI API saja.

**Sesudah:** ditambahkan **Hybrid LLM** — bisa switch antara OpenAI dan Ollama via environment variable `LLM_PROVIDER` di `.env`:
```env
LLM_PROVIDER=openai   # pakai OpenAI API (default)
LLM_PROVIDER=ollama   # pakai Ollama lokal (butuh GPU)
```

---

## Bug Ditemukan (Belum Diperbaiki)

### `frontend/lib/api.ts` — Upload Recording 422
**Jobdesk:** Frontend (Helena)

**Masalah:** Baris 125-128, header `Content-Type: multipart/form-data` di-set manual tanpa `boundary`. Server tidak bisa parse body multipart dan return 422 Unprocessable Entity.

**Fix:**
```ts
// Sebelum (salah)
headers: { "Content-Type": "multipart/form-data" }

// Sesudah (benar)
headers: { "Content-Type": undefined }
```

---

## Catatan Menjalankan Lokal (Tanpa Docker)

Untuk development tanpa Docker, semua service tetap bisa jalan manual. Yang wajib tetap pakai Docker hanya infrastruktur (postgres, redis, minio, mailhog):

```bash
# Infra saja
docker compose up -d postgres redis minio mailhog

# Backend (terminal terpisah, env meetmate)
cd backend && uvicorn app.main:app --reload --port 8000

# Celery Worker (terminal terpisah, env meetmate, dari root project)
set PYTHONPATH=e:\Folder audi\MeetMate\Aplikasi\backend;e:\Folder audi\MeetMate\Aplikasi
celery -A app.worker worker --loglevel=info

# Frontend (terminal terpisah)
cd frontend && npm run dev
```
