# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Kioku is a self-hosted meeting management app. It covers the full meeting lifecycle: scheduling → email invitations → attendance check-in → audio upload → ML transcription/summarization → notulen distribution. Infrastructure (DB, storage, email) is self-hosted. Transcription and summarization go through a cloud LLM API (Gemini by default, OpenAI optional; see "ML Pipeline Setup" below), so audio and transcript text are **not** kept fully on-machine. Speaker labels come from Gemini itself when `LLM_PROVIDER=gemini`; with other providers they come from optional local diarization via pyannote.audio (only installed when `INSTALL_LOCAL_DIARIZATION=true`).

**Team:** Audi (Backend), Helena (Frontend), Azmi (ML)

---

## Development Commands

We use a fully dockerized workflow. You do not need to install Python or Node.js locally.

### Start Everything (Frontend, Backend API, ML Celery Worker, Postgres, Redis, MinIO, Mailhog)
```bash
make up
```
This builds all Docker images and starts them in the background.

To rebuild containers after changing `requirements.txt` or `package.json`:
```bash
make build
```

### Database Migrations
```bash
make migrate   # runs `alembic upgrade head` inside the backend-api container
```
Usually unnecessary — backend-api already runs `alembic upgrade head` on every container start (see `backend/Dockerfile.api`). Keep using `make migrate` when you want to apply a migration without restarting the container.

Create a new migration after changing SQLAlchemy models:
```bash
docker compose exec backend-api alembic revision --autogenerate -m "description"
make migrate
```

**Alembic + PostgreSQL enum pattern:** Jangan pakai `sa.Enum()` di dalam `op.create_table()` untuk kolom enum. `sa.Enum` mengabaikan `create_type=False`, sehingga SQLAlchemy mencoba membuat ulang tipe yang sudah ada dan melempar `DuplicateObject`. Pola yang benar:

```python
# 1. Buat semua enum type di awal upgrade() dengan checkfirst=True
postgresql.ENUM("foo", "bar", name="myenum").create(op.get_bind(), checkfirst=True)

# 2. Pakai postgresql.ENUM(create_type=False) di dalam create_table
sa.Column("col", postgresql.ENUM("foo", "bar", name="myenum", create_type=False))
```

### Logs
```bash
make logs         # all logs
make logs-api     # backend API logs
make logs-worker  # celery worker logs
```

### Reset Database
```bash
make down-v   # stops all containers AND deletes volumes (full DB wipe)
```
Run `make up && make migrate` after this to start fresh.

### Pre-commit
```bash
make pre-commit   # runs pre-commit hooks against all files manually
```

### Backend Tests
```bash
make test   # runs pytest inside the backend-api container
```
Tests run against a separate `<db>_test` Postgres database (auto-created and migrated to head on first run, same container as dev) — never the dev database. After adding `pytest`/`httpx` or other new backend deps, rebuild first: `docker compose build backend-api`.

### Bootstrap Admin / Superadmin

Automatic, via `SUPERADMIN_*` / `ADMIN_*` in `.env` — no command needed. The backend-api container runs `alembic upgrade head` then `python -m app.services.seed` before uvicorn (see `backend/Dockerfile.api`), so the accounts exist as soon as `make up` finishes, including after a `make down-v` wipe.

```env
SUPERADMIN_EMAIL=super@kioku.test
SUPERADMIN_PASSWORD=ganti-ini
ADMIN_EMAIL=admin@kioku.test
ADMIN_PASSWORD=ganti-ini
```

Each email/password pair is optional; if only one half of a pair is set, that pair is skipped with a warning. Names are fixed (`Super Admin`, `Admin`) and can be changed from the profile page. Applying a change to these variables only needs a restart (`docker compose up -d backend-api`), not a rebuild — `.env` is read at container start.

Seeding rules (`backend/app/services/seed.py`), designed to be safe to re-run on every boot:
- Email not present → account created
- Email already present → **password and name are never overwritten**
- Existing role lower than the seeded role → promoted, and written to `AuditLog` with `actor_id = NULL` (system action). This is also how you turn an account that already self-registered as `user` into a superadmin.
- Existing role equal or higher → left alone; **the seeder never demotes**

A half-filled pair or an unexpected seeder error never blocks startup — the seeder logs `[seed] ... dilewati` / `DILEWATI` to stderr and the API boots normally. A failed migration *does* stop the container, deliberately.

`backend/scripts/seed_admin.py` still exists for creating a one-off superadmin without putting its password in `.env`; unlike the auto-seeder it refuses if the email already exists. Promote/demote after bootstrap is normally done via `PATCH /admin/users/:id/role` (superadmin only) or the `/admin/users` page.

### Frontend Commands (if needed locally)
Adding shadcn components is still done from inside the frontend folder (requires local Node.js):
```bash
cd frontend
npx shadcn-ui@latest add <component-name>
```

### Configuration — one place for every setting

**Every tunable value lives in the root `.env`** (template: `.env.example`, which documents each setting). Never hardcode a limit, timeout, retry count, model name, polling interval or similar number in code, and never create another `.env` file (`backend/.env`, `frontend/.env.local`) — the backend only reads the root one.

To add a new setting:
1. Add the field (with its default) to `Settings` in `backend/app/config.py` — this is the only place a default may live.
2. Document it in `.env.example` (`backend/tests/test_env_example.py` fails if you forget).
3. Read it through `settings.X` in backend code.
4. If `ml/` needs it: add the name to `_ML_ENV_KEYS` in `backend/app/tasks/process_recording.py`, and read it in ML with `require_env("X")` from `ml/env.py` (no defaults inside `ml/`; it must not import backend code).
5. If the frontend needs it: add it to `PublicConfigResponse` (`schemas/config.py`) + `routers/config.py` + `AppConfig` in `frontend/types/index.ts`, and read it via `useAppConfig()`. `GET /api/v1/config` has no auth, so **never expose secrets there** (`test_public_config.py` pins the exact field list). Don't duplicate the value as a frontend constant.

Apply a change: `docker compose up -d backend-api celery-worker celery-beat` (no rebuild). Only `NEXT_PUBLIC_*` values need `docker compose up -d --build frontend`, because Next.js inlines them at build time.

### ML Pipeline Setup
Transcription, summary, and action item extraction run on a switchable LLM provider — **Gemini** (default, what production runs) or **OpenAI**. Toggle via `LLM_PROVIDER` in `.env`, then `docker compose build celery-worker && docker compose up -d celery-worker` to apply:
```env
LLM_PROVIDER=gemini   # or 'openai'

OPENAI_API_KEY=...
OPENAI_TRANSCRIBE_MODEL=whisper-1
OPENAI_MODEL=gpt-4o-mini

GEMINI_API_KEY=...
GEMINI_MODEL=gemini-3.1-flash-lite
```
`gemini-3.1-flash-lite` had a reported upstream bug returning `500 INTERNAL` on audio input (June 2026); production currently runs it fine, but if audio transcription starts failing with that error, suspect the model first and try another `GEMINI_MODEL`. OpenAI is not used right now (its billing ran out), and `whisper-1` is scheduled to be retired by OpenAI on 2027-02-26. 
**Diarization is provider-dependent and optional.** With `LLM_PROVIDER=gemini`, `diarize()` returns `[]` immediately (Gemini labels speakers in the transcription prompt) and torch/pyannote are never touched. With any other provider it needs local pyannote.audio, which is installed into the `celery-worker` image only when `INSTALL_LOCAL_DIARIZATION=true` (default `false`; packages in `ml/requirements-diarization.txt`). This is a **build-time** switch, not a runtime one: after changing it run `make build`. If a non-Gemini provider runs without it installed, the recording fails with a clear `PermanentMLError`, not a silent `SPEAKER_00`. It is the one setting that is *not* a field in `config.py` (it is a Docker build arg, passed via `docker-compose.yml`), but it is still documented in `.env.example`.

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

### Data Flow for Recording Processing

1. Organizer uploads audio → `POST /meetings/:id/recording`
2. Backend saves file to MinIO, enqueues Celery task
3. Celery worker calls ML pipeline in sequence:
   - `transcribe(audio_path)` → OpenAI Whisper API or Gemini API, depending on `LLM_PROVIDER`
   - `diarize(audio_path)` → skipped (`[]`) when `LLM_PROVIDER=gemini`; otherwise pyannote.audio, local, requires `INSTALL_LOCAL_DIARIZATION=true`
   - `merge_transcript_diarization(transcript, diarization)`
   - `extract_summary(transcript_text)` → OpenAI or Gemini, depending on `LLM_PROVIDER`
   - `extract_action_items(transcript_text, participant_names)` → OpenAI or Gemini, depending on `LLM_PROVIDER`
4. Results saved to DB (Transcript, Summary, ActionItem tables)
5. Email distributed to all participants automatically

Frontend polls `GET /meetings/:id/recording/status` every `RECORDING_POLL_INTERVAL_SECONDS` (default 3) until status is `completed` or `failed`.

**`ProcessingStatus` pipeline stages** (in order): `queued` → `transcribing` → `diarizing` → `extracting` → `sending_email` → `completed` | `failed`. Individual step completion is tracked in `recording.processing_steps` (JSONB). On failure, `recording.error_message` contains the reason.

### Backend Structure (`backend/app/`)

- `main.py` — FastAPI app, router registration
- `worker.py` — Celery app instance
- `config.py` — `Settings` loaded from the root `.env`; schema + defaults for every setting (see "Configuration" above)
- `database.py` — SQLAlchemy session
- `routers/` — HTTP endpoints (auth, meetings, recordings, checkin)
- `models/` — SQLAlchemy ORM models (map 1:1 to DB tables)
- `schemas/` — Pydantic request/response schemas
- `services/` — Business logic (auth, meeting, storage, email, pipeline)
- `tasks/process_recording.py` — Main Celery task that orchestrates ML calls

### ML Structure (`ml/`)

- `env.py` — `require_env(name)`: reads a setting from the environment, raises a clear error if missing (no defaults here)
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
- `lib/api.ts` — axios instance; JWT auto-attached via request interceptor; 401 clears storage + redirects to `/login`
- `lib/utils.ts` — `cn()` (tailwind merge), `isDateOverdue()` (timezone-safe), `extractApiError()` (parses FastAPI `detail` field)
- `types/index.ts` — TypeScript types derived from API contract
- `hooks/` — React Query wrappers: `useRecordingStatus`, `useUploadRecording`, `useDeleteRecording`, `useMyActionItems`, `useUpdateActionItem`

**Frontend state management:** Server state uses `@tanstack/react-query`. Auth token stored in `localStorage` under `access_token` (and mirrored to a cookie so Next.js middleware can read it). User profile cached in `localStorage` under `user_profile` — always parse with `try/catch` since corrupt JSON crashes the main layout.

**React Query cache keys:** `["meeting", id]`, `["recording-status", meetingId]`, `["action-items"]`. When a mutation touches meeting data (e.g. updating an action item), invalidate both `["action-items"]` and `["meeting", meetingId]` — invalidating only one leaves the detail page stale.

**Frontend env var:** Set `NEXT_PUBLIC_API_URL` to override the default API base (`http://localhost:8000/api/v1`).

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

## Known Schema Gaps

- **`PATCH /action-items/:id`** — `ActionItemUpdateRequest` (`schemas/action_item.py`) **does** include `assignee_participant_id` (added in PR #8). Backend model `ActionItem` assigns via `assignee_participant_id` FK to `meeting_participants.id`, not directly to `users.id`.

(The previous entry here about `PATCH /meetings/:id` not accepting `participant_emails` is no longer accurate — `MeetingUpdate` supports it and `update_meeting()` fully implements add/remove of participants, including sending invitations to newly-added ones.)

---

## Auth Model

JWT + bcrypt, plus optional Google SSO. `User.role` (`user` | `admin` | `superadmin`, default `user`, defined in `backend/app/models/user.py`) is a **global** role stored on the account — separate from per-meeting roles, which are determined by the `MeetingParticipant` relation (organizer vs peserta) and never touch `User.role`.

**Admin & superadmin** (`routers/admin.py`, 10 endpoints): suspend/unsuspend users — enforced on every request via `_decode_user_token`, not just at login, so a suspended user is kicked out immediately rather than merely blocked from re-login. Promote/demote between `user`/`admin`/`superadmin` is guarded so the last active superadmin can't be demoted. Superadmin-triggered password reset sends an emailed reset link rather than setting the password directly. Opening another user's meeting content requires a fresh justification *every time* it's opened (not granted once and reused); that access, plus every role/suspend change, is written to `AuditLog`, scoped by actor for admins vs. full visibility for superadmins. Admins can soft-delete meetings/recordings, which shows participants a generic deletion notice rather than the content. First superadmin is bootstrapped manually via `scripts/seed_admin.py` (see Development Commands above); every subsequent admin/superadmin is created via promote, not the script.

Magic-link check-in tokens are single-use and do not require login. They intentionally never expire (participants can revisit the check-in portal — notulen, action items — at any time); the check-in *action* itself is separately gated by `attendance_locked` and by the meeting's `scheduled_at + duration_minutes` window.

**Google SSO:** `POST /auth/google` accepts `{ "id_token": "<Google ID token>" }` (verified via `google-auth` against `GOOGLE_CLIENT_ID`, not the authorization-code flow) and returns the same `TokenResponse` shape as `POST /auth/login`. `User.password_hash` is nullable — Google-only accounts have no password. `User.auth_provider` (`"local"` | `"google"`) records how the account was first created; `User.google_sub` is the unique Google account identifier used to look up returning Google users. **Account linking is automatic**: if a Google login's email matches an existing local (password) account, `google_sub` is attached to that same account rather than creating a duplicate — Google always verifies email ownership, so same email is treated as the same person. No domain restriction (`hd` claim) is currently enforced; any Google account can sign in. Toggle the whole feature off via `GOOGLE_SSO_ENABLED=false` in `.env` (endpoint returns 404 when disabled) without a redeploy.

---

## Google Calendar Sync

Push-only sync (Kioku → Google, never the reverse): `create_meeting()`/`update_meeting()`/`delete_meeting()` in `services/meeting.py` enqueue Celery tasks from `tasks/calendar_sync.py` after commit — never called synchronously from the request handler. A failed sync never fails the meeting request; errors are logged and swallowed per-participant so one broken token doesn't block the others.

**Fan-out is per-participant, not organizer-only:** every `MeetingParticipant` with a `user_id` who has individually connected their Google account (`GoogleCalendarCredential.connected = true`) gets the event pushed to *their own* calendar. This means one meeting can have N different Google events (one per connected participant), tracked via `CalendarSyncEvent` (unique on `meeting_participant_id`) — there is deliberately no single `google_event_id` column on `meetings`. Removing a participant from a meeting does **not** clean up their already-synced Google event (the `CalendarSyncEvent` row cascades away with the `MeetingParticipant`, but the real event is left orphaned on their calendar) — this gap is accepted, not yet handled.

**OAuth flow is authorization-code (not the SSO's ID-token flow)**, since it needs a long-lived `refresh_token`: `GET /auth/google/calendar/connect` → redirects to Google consent (scope `calendar.events`, `access_type=offline`, `prompt=consent` to force a refresh token every time) → `GET /auth/google/calendar/callback` exchanges the code and stores tokens **encrypted at rest** (`services/crypto.py`, Fernet, key in `GOOGLE_TOKEN_ENCRYPTION_KEY`). Both of these two endpoints are reached via full-page browser redirect (`window.location.href`, not axios), so they authenticate off the `access_token` **cookie** (`get_current_user_from_cookie`), not the `Authorization` header — the OAuth `state` param is itself a short-lived signed JWT (`purpose: calendar_connect`, 10 min) carrying the user id, so the callback doesn't need the cookie again. `GET /me/calendar-status` and `DELETE /auth/google/calendar` are normal Bearer-authenticated JSON endpoints.

Access tokens auto-refresh before each API call (`services/calendar.py::get_valid_access_token`); if the refresh fails with `invalid_grant` (user revoked access from their Google account settings, not via Kioku's Disconnect button), the credential is marked `connected = false` so `/me/calendar-status` reflects reality instead of silently going stale.

Event content is intentionally minimal: title + time + location only — `description`/`agenda_text` are never sent to Google (privacy tradeoff, same reasoning as the transcript/cloud-LLM note above). `attendees` is never populated, so Google never sends its own invite emails on top of Kioku's existing ones.

Toggle the whole feature off via `GOOGLE_CALENDAR_SYNC_ENABLED=false` in `.env` — hides `/auth/google/calendar/connect` and disables the Celery sync tasks (they no-op) without a redeploy.

---

## Storage

- Dev: MinIO (local S3-compatible, docker compose)
- Prod target: Cloudflare R2
- Access via `services/storage.py` using boto3 S3 client

Audio file limits (defaults; change in `.env` via `ALLOWED_AUDIO_FORMATS`, `MAX_UPLOAD_SIZE_MB`, `MAX_AUDIO_DURATION_HOURS`): mp3/mp4/wav/m4a, max 200MB, max 2 hours.
