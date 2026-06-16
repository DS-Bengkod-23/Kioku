# PR: Integrasi Docker + Perbaikan Docs — Branch `merge` → `main`

## Ringkasan

Branch `merge` mengintegrasikan hasil kerja tiga jobdesk (Backend/Audi, Frontend/Helena, ML/Azmi) dan menambahkan lapisan infrastruktur Docker agar semua service bisa dijalankan dari satu perintah. PR ini juga memperbaiki bug-bug integrasi yang ditemukan saat testing dan memperbarui seluruh dokumentasi agar sesuai kondisi kode yang sebenarnya.

---

## Ringkasan per Jobdesk

### Backend (Audi)

**`backend/app/tasks/process_recording.py`**
- Tambah injeksi `os.environ` di awal task agar ML modules bisa baca config via `os.getenv()` — sebelumnya semua setting (HF_TOKEN, OPENAI_API_KEY, dll) selalu `None` karena `pydantic_settings` tidak otomatis populate `os.environ`

**`backend/app/schemas/meeting.py`**
- Fix `GET /meetings/{id}` → 500: setelah pipeline selesai, field `transcript`, `summary`, `action_items` berisi SQLAlchemy ORM object yang tidak bisa di-serialize Pydantic. Fix: convert ke plain dict di `extract_fields` validator

**`backend/README.md`** & **`backend/usage.md`**
- Perbarui daftar routers, models, schemas, services sesuai kondisi kode aktual
- Tambah catatan `--pool=solo` untuk Windows, arahkan ke `scripts/start-worker.bat`

---

### Frontend (Helena)

**`frontend/lib/api.ts`**
- Fix `POST /meetings/{id}/recording` → 422: header `Content-Type` jangan di-set manual untuk `multipart/form-data`, biarkan axios yang set otomatis (dengan boundary yang benar)

**`frontend/README.md`**
- Perbaiki nama hook: `useProcessingStatus.ts` → `useRecording.ts`
- Tambah hook yang hilang: `useMeeting.ts`, `useActionItems.ts`
- Tambah halaman `[id]/edit/` di struktur folder
- Section "Halaman yang Perlu Dibuat" → "Daftar Halaman" (semua sudah selesai dibuat)

---

### ML (Azmi)

**`ml/diarize.py`**
- Fix Windows compatibility: `torchcodec` (audio backend pyannote) tidak bisa load karena butuh FFmpeg shared DLLs, sedangkan yang tersedia hanya static binary `ffmpeg.exe`
- Solusi cross-platform: fungsi `_load_audio()` — coba `torchaudio.load()` dulu (jalan normal di Mac/Linux), jika gagal otomatis fallback ke `ffmpeg` subprocess + `soundfile` (Windows)
- Tidak ada perubahan pada function signature — kompatibel penuh dengan backend

**`ml/requirements.txt`**
- Tambah komentar di atas: ffmpeg adalah system dependency (bukan pip), cara install via conda atau download manual

**`ml/README.md`**
- Stack: perbarui LLM dari "Ollama only" → "Hybrid (OpenAI default / Ollama opsional)"
- Setup: tambah langkah install ffmpeg, konfigurasi HF_TOKEN via `.env`
- Hapus referensi folder `notebooks/` yang tidak ada

---

## Perubahan

### 1. Dockerization

**File baru:**

| File | Keterangan |
|---|---|
| `docker-compose.yml` | Orkestrasi semua service (postgres, redis, minio, mailhog, backend-api, celery-worker, frontend) |
| `Makefile` | Shortcut commands: `make up`, `make build`, `make migrate`, `make logs`, dll |
| `scripts/make.bat` | Versi Windows dari Makefile |
| `scripts/start-worker.bat` | Launcher Celery worker Windows — otomatis set PYTHONPATH dan `--pool=solo` |
| `scripts/start-worker.sh` | Launcher Celery worker Mac/Linux |
| `backend/Dockerfile` | Image backend API + migration |
| `backend/Dockerfile.worker` | Image Celery worker dengan ML dependencies (CPU-only PyTorch) |
| `frontend/Dockerfile` | Image Next.js frontend |
| `docs/DOCKER_CHANGES.md` | Catatan lengkap semua perubahan yang masuk karena Docker |
| `docs/DOCKER_WORKFLOW.md` | Panduan developer untuk workflow Docker (Hybrid LLM, pre-commit, dll) |

**File dimodifikasi:**

| File | Perubahan |
|---|---|
| `docker-compose.yml` | Tambah env overrides agar container bisa saling terhubung (`localhost` → nama service) |
| `backend/app/config.py` | Tambah field Settings yang kurang: `LLM_PROVIDER`, `OPENAI_API_KEY`, `OPENAI_MODEL`, `HF_TOKEN`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL` — sebelumnya menyebabkan `ValidationError` saat startup |
| `ml/requirements.txt` | Tambah `--extra-index-url` CPU-only PyTorch agar build tidak timeout download CUDA |
| `backend/Dockerfile.worker` | Tambah flag CPU-only PyTorch saat install |
| `backend/.dockerignore` | Hapus `alembic.ini` dari ignore list (menyebabkan `make migrate` gagal) |
| `.gitignore` | Tambah `review-pr/` ke bagian Internal/Local Only |
| `README.md` | Tulis ulang lengkap: diagram arsitektur Mermaid, dua mode run (Full Docker & Hybrid), panduan LLM provider |

**File dihapus:**

| File | Alasan |
|---|---|
| `make.bat` | Dipindah ke `scripts/make.bat` agar lebih rapi |
| `review-pr/` | Catatan review internal — tidak perlu masuk ke repository |

---

### 2. Bug Fix Integrasi

| Bug | Penyebab | Fix | File |
|---|---|---|---|
| `POST /meetings/{id}/recording` → 422 Unprocessable Entity | `Content-Type: multipart/form-data` di-set manual tanpa boundary | Set header ke `undefined` agar axios auto-set dengan boundary | `frontend/lib/api.ts` |
| `GET /meetings/{id}` → 500 PydanticSerializationError (recording) | `recording: Optional[Any]` tidak bisa serialize SQLAlchemy model | Ganti ke `recording: Optional[RecordingResponse]` | `backend/app/schemas/meeting.py` |
| `GET /meetings/{id}` → 500 PydanticSerializationError (transcript/summary/action_items) | SQLAlchemy ORM objects dikembalikan langsung sebagai `Optional[Any]` ke Pydantic | Convert ke plain dict di `extract_fields` validator | `backend/app/schemas/meeting.py` |
| ML modules (`os.getenv("HF_TOKEN")`) selalu return `None` | `pydantic_settings` baca `.env` ke object `settings`, tapi tidak inject ke `os.environ` | Tambah `os.environ.setdefault(...)` di awal task sebelum import ML | `backend/app/tasks/process_recording.py` |
| pyannote diarization crash di Windows: `libtorchcodec_core5.dll` / `AudioDecoder` | `torchcodec` butuh FFmpeg shared DLLs; static binary `ffmpeg.exe` tidak menyediakannya | Fungsi `_load_audio()` — coba `torchaudio.load()` dulu (Mac/Linux), fallback ke `ffmpeg` subprocess + `soundfile` (Windows) | `ml/diarize.py` |
| Celery worker crash di Windows: `ValueError: not enough values to unpack` | Windows tidak support `fork()` untuk Celery | Tambah `--pool=solo` — sudah otomatis di `scripts/start-worker.bat` | `scripts/start-worker.bat` |
| `make migrate` gagal: `No script_location key found` | `alembic.ini` ada di `backend/.dockerignore` | Hapus dari `.dockerignore` | `backend/.dockerignore` |
| `make migrate` gagal: `connection refused port 5432` | Container backend pakai `localhost` tapi harusnya nama service `postgres` | Tambah environment overrides di `docker-compose.yml` | `docker-compose.yml` |

---

### 3. Akurasi Dokumentasi

Seluruh README dan docs diperbarui agar sesuai kondisi kode yang sebenarnya:

**`frontend/README.md`**
- Nama hook diperbaiki: `useProcessingStatus.ts` → `useRecording.ts`
- Tambah hook yang hilang: `useMeeting.ts`, `useActionItems.ts`
- Tambah halaman `[id]/edit/` di struktur folder
- Perbarui daftar `components/ui/` (tambah `alert-dialog.tsx`, `form-error.tsx`)
- Section "Halaman yang Perlu Dibuat" → "Daftar Halaman" (semua sudah dibuat)

**`backend/README.md`**
- Routers: tambah `action_items.py`
- Models: tambah `attendance.py`, `invitation.py`
- Schemas: tambah `action_item.py`, `checkin.py`
- Services: hapus `pipeline.py` (tidak ada), tambah `recording.py`, `action_item.py`, `invitation.py`, `checkin.py`
- Celery: arahkan ke `scripts/start-worker.bat`, tambah catatan `--pool=solo` untuk Windows

**`ml/README.md`**
- Stack: "Ollama + qwen2.5:7b" → "Hybrid LLM (OpenAI API / Ollama qwen2.5:7b)"
- Setup: OpenAI jadi default (urutan pertama), Ollama jadi opsional
- Hapus referensi folder `notebooks/` yang tidak ada
- HF_TOKEN sekarang lewat `.env`, bukan `export` manual

**`backend/usage.md`**
- Celery command: tambah `--pool=solo`, arahkan ke `scripts/start-worker.bat`
- `docker compose up -d` → `docker compose up -d postgres redis minio mailhog` (infra saja, bukan semua service)

---

## Cara Menjalankan Setelah Merge

```bash
# 1. Copy env
cp .env.example .env
# Isi OPENAI_API_KEY dan HF_TOKEN di .env

# 2. Jalankan semua (Full Docker)
make up
make migrate

# Atau mode Hybrid (development)
docker compose up -d postgres redis minio mailhog
cd backend && uvicorn app.main:app --reload --port 8000
scripts\start-worker.bat   # terminal baru (Windows)
cd frontend && npm run dev  # terminal baru
```

---

## Checklist

- [x] Backend API jalan dan bisa diakses di `http://localhost:8000/docs`
- [x] Frontend jalan di `http://localhost:3000`
- [x] Upload recording berhasil (fix 422)
- [x] Detail meeting tampil benar setelah pipeline selesai (fix 500)
- [x] Celery worker berjalan di Windows dengan `--pool=solo`
- [x] `make migrate` berhasil membuat semua tabel
- [x] Pipeline ML end-to-end jalan: Whisper → pyannote diarization → OpenAI extraction → email
- [x] pyannote diarization kompatibel Windows (ffmpeg fallback) dan Mac/Linux (torchaudio)
- [x] Transcript, summary, action items tersimpan ke DB dan tampil di frontend
- [x] Semua dokumentasi sesuai kondisi kode aktual

---

## Reviewer Notes

- **`scripts/start-worker.bat`** — wajib dijalankan dari root project, bukan dari dalam `backend/`. Script ini yang menghandle PYTHONPATH.
- **LLM Provider** — default sekarang `openai`. Untuk pakai Ollama lokal, set `LLM_PROVIDER=ollama` di `.env`.
- **Whisper model** — default `large-v3` (2.88GB). Untuk laptop RAM terbatas, set `WHISPER_MODEL=small` di `.env`.
- **MinIO** — bucket `meetmate-recordings` perlu dibuat manual pertama kali via console `http://localhost:9001` (minioadmin/minioadmin).
