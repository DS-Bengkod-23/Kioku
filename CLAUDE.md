# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MeetMate is a fully self-hosted, offline-first meeting management app. It covers the full meeting lifecycle: scheduling → email invitations → attendance check-in → audio upload → ML transcription/summarization → notulen distribution. No data leaves the machine; all ML runs locally.

**Team:** Audi (Backend), Helena (Frontend), Azmi (ML)

---

## Development Commands

### Infrastructure (run first)
```bash
docker compose up -d
```
This starts PostgreSQL (5432), Redis (6379), MinIO (9000/9001), and Mailhog (1025/8025).

### Backend
```bash
cd backend
pip install -r requirements.txt
alembic upgrade head                          # run migrations
uvicorn app.main:app --reload --port 8000     # API server
celery -A app.worker worker --loglevel=info   # background worker (separate terminal)
```

Create a new migration after changing SQLAlchemy models:
```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
```

**Alembic + PostgreSQL enum pattern:** Jangan pakai `sa.Enum()` di dalam `op.create_table()` untuk kolom enum. `sa.Enum` mengabaikan `create_type=False`, sehingga SQLAlchemy mencoba membuat ulang tipe yang sudah ada dan melempar `DuplicateObject`. Pola yang benar:

```python
# 1. Buat semua enum type di awal upgrade() dengan checkfirst=True
postgresql.ENUM("foo", "bar", name="myenum").create(op.get_bind(), checkfirst=True)

# 2. Pakai postgresql.ENUM(create_type=False) di dalam create_table
sa.Column("col", postgresql.ENUM("foo", "bar", name="myenum", create_type=False))
```

### Frontend
```bash
cd frontend
npm install
npm run dev    # http://localhost:3000
```

Requires `frontend/.env.local`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

Add shadcn components with:
```bash
npx shadcn-ui@latest add <component-name>
```

### ML Pipeline
```bash
ollama pull qwen2.5:7b
ollama serve                    # must be running before Celery worker starts
cd ml
pip install -r requirements.txt
export HF_TOKEN=your_token     # required for pyannote first-time model download
python evaluation/evaluate.py  # measure WER + action item F1
```

---

## Architecture

### Service Map

| Service | Port | Purpose |
|---|---|---|
| Frontend (Next.js) | 3000 | UI |
| Backend (FastAPI) | 8000 | REST API + docs at /docs |
| Celery Worker | — | Async ML processing |
| PostgreSQL | 5432 | Primary DB |
| Redis | 6379 | Celery broker + result backend |
| MinIO | 9000/9001 | Local file storage (S3-compatible) |
| Mailhog | 8025 | Email preview in dev |
| Ollama | 11434 | Local LLM inference |

### Data Flow for Recording Processing

1. Organizer uploads audio → `POST /meetings/:id/recording`
2. Backend saves file to MinIO, enqueues Celery task
3. Celery worker calls ML pipeline in sequence:
   - `transcribe(audio_path)` → Whisper large-v3
   - `diarize(audio_path)` → pyannote.audio
   - `merge_transcript_diarization(transcript, diarization)`
   - `extract_summary(transcript_text)` → Ollama qwen2.5:7b
   - `extract_action_items(transcript_text, participant_names)` → Ollama
4. Results saved to DB (Transcript, Summary, ActionItem tables)
5. Email distributed to all participants automatically

Frontend polls `GET /meetings/:id/recording/status` to track pipeline progress.

### Backend Structure (`backend/app/`)

- `main.py` — FastAPI app, router registration
- `worker.py` — Celery app instance
- `config.py` — Settings loaded from `.env`
- `database.py` — SQLAlchemy session
- `routers/` — HTTP endpoints (auth, meetings, recordings, checkin)
- `models/` — SQLAlchemy ORM models (map 1:1 to DB tables)
- `schemas/` — Pydantic request/response schemas
- `services/` — Business logic (auth, meeting, storage, email, pipeline)
- `tasks/process_recording.py` — Main Celery task that orchestrates ML calls

### ML Structure (`ml/`)

- `schemas.py` — Shared Pydantic types: `TranscriptResult`, `SummaryResult`, `ActionItem`, `TranscriptSegment`
- `transcribe.py` — `transcribe(audio_path) -> TranscriptResult`
- `diarize.py` — `diarize(audio_path) -> list[TranscriptSegment]`, `merge_transcript_diarization(...)`
- `extract.py` — `extract_summary(transcript_text) -> SummaryResult`, `extract_action_items(...) -> list[ActionItem]`
- `prompts/` — LLM prompt templates (do not hardcode prompts inline)
- `notebooks/` — Dev experiments only, not imported by backend
- `evaluation/` — Golden dataset + `evaluate.py` for WER/F1 metrics

Backend imports ML directly (not via HTTP):
```python
from ml.transcribe import transcribe
from ml.diarize import diarize, merge_transcript_diarization
from ml.extract import extract_summary, extract_action_items
```

### Frontend Structure (`frontend/`)

- `app/` — Next.js 14 App Router pages
  - `(auth)/` — login, register (no auth required)
  - `meetings/` — dashboard list, create form, detail page
  - `check-in/[token]/` — public check-in page (no auth)
  - `action-items/` — user's own action items
- `components/` — grouped by domain (meetings/, recording/, notulen/)
- `components/ui/` — shadcn auto-generated, do not edit manually
- `lib/api.ts` — central fetch/axios wrapper for all API calls
- `types/index.ts` — TypeScript types derived from API contract
- `hooks/useProcessingStatus.ts` — polls recording status endpoint

---

## Key Contracts

### API Base URL
`http://localhost:8000/api/v1`

All endpoints except `/auth/*` and `/check-in/*` require `Authorization: Bearer <jwt_token>`.

Error responses always use: `{ "detail": "message" }`

### ML Function Signatures (frozen — do not change without coordinating with Backend)

```python
def transcribe(audio_path: str) -> TranscriptResult
def diarize(audio_path: str) -> list[TranscriptSegment]
def merge_transcript_diarization(transcript: TranscriptResult, diarization: list[TranscriptSegment]) -> TranscriptResult
def extract_summary(transcript_text: str) -> SummaryResult
def extract_action_items(transcript_text: str, participant_names: list[str]) -> list[ActionItem]
```

All ML functions must raise specific exceptions (not silent fail) and return Pydantic models (not dicts).

### Git Workflow

- Branch naming: `feature/<role>-<name>` (e.g. `feature/backend-upload-endpoint`)
- Never push directly to `main`; PR with at least 1 reviewer
- `main` must always be deployable

---

## Auth Model

JWT + bcrypt. Single global user role; per-meeting roles are determined by the `MeetingParticipant` relation (organizer vs peserta). Magic-link check-in tokens are single-use, expire 24h after meeting ends, and do not require login.

---

## Storage

- Dev: MinIO (local S3-compatible, docker compose)
- Prod target: Cloudflare R2
- Access via `services/storage.py` using boto3 S3 client

Audio file limits: mp3/mp4/wav/m4a, max 200MB, max 2 hours.
