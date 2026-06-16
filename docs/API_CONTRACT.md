# API Contract

**Base URL:** `http://localhost:8000/api/v1`
**Status:** Draft v0.1

## Authentication

Semua endpoint kecuali `/auth/*` dan `/check-in/*` butuh header:
```
Authorization: Bearer <jwt_token>
```

---

## Auth

### POST /auth/register
**Request:**
```json
{
  "name": "Audi",
  "email": "audi@email.com",
  "password": "password123"
}
```
**Response 201:**
```json
{
  "id": "uuid",
  "name": "Audi",
  "email": "audi@email.com"
}
```

### POST /auth/login
**Request:**
```json
{
  "email": "audi@email.com",
  "password": "password123"
}
```
**Response 200:**
```json
{
  "access_token": "jwt_token_here",
  "token_type": "bearer",
  "id": "uuid",
  "name": "Audi",
  "email": "audi@email.com"
}
```

---

## Meetings

### POST /meetings
Buat meeting baru. Organizer otomatis jadi participant dengan role organizer.

**Request:**
```json
{
  "title": "Sprint Planning Week 3",
  "scheduled_at": "2026-06-01T09:00:00",
  "location": "Meeting Room A",
  "description": "Planning sprint minggu ini",
  "agenda_text": "1. Review backlog\n2. Estimasi task\n3. Assign task",
  "participant_emails": ["helena@email.com", "azmi@email.com"]
}
```
**Response 201:**
```json
{
  "id": "uuid",
  "title": "Sprint Planning Week 3",
  "scheduled_at": "2026-06-01T09:00:00",
  "location": "Meeting Room A",
  "description": "Planning sprint minggu ini",
  "agenda_text": "1. Review backlog\n2. Estimasi task\n3. Assign task",
  "status": "scheduled",
  "organizer": {
    "id": "uuid",
    "name": "Audi",
    "email": "audi@email.com"
  },
  "participants": [
    {
      "id": "uuid",
      "email": "helena@email.com",
      "name": "Helena",
      "role": "peserta",
      "attendance_status": "pending"
    }
  ],
  "created_at": "2026-05-25T10:00:00"
}
```

### GET /meetings
List semua meeting milik user yang login (sebagai organizer atau peserta).

**Query params:**
- `page` (default: 1)
- `limit` (default: 10)
- `status` (optional): `scheduled`, `completed`, `cancelled`

**Response 200:**
```json
{
  "items": [
    {
      "id": "uuid",
      "title": "Sprint Planning Week 3",
      "scheduled_at": "2026-06-01T09:00:00",
      "location": "Meeting Room A",
      "status": "scheduled",
      "participant_count": 3,
      "attendance_count": 2,
      "has_recording": false,
      "processing_status": null
    }
  ],
  "total": 12,
  "page": 1,
  "limit": 10
}
```

### GET /meetings/:id
Detail meeting lengkap dengan transcript, summary, action items.

**Response 200:**
```json
{
  "id": "uuid",
  "title": "Sprint Planning Week 3",
  "scheduled_at": "2026-06-01T09:00:00",
  "location": "Meeting Room A",
  "description": "...",
  "agenda_text": "...",
  "status": "completed",
  "organizer": { "id": "uuid", "name": "Audi", "email": "audi@email.com" },
  "participants": [
    {
      "id": "uuid",
      "email": "helena@email.com",
      "name": "Helena",
      "role": "peserta",
      "attendance_status": "hadir"
    }
  ],
  "recording": {
    "id": "uuid",
    "file_url": "recordings/uuid/audio.mp3",
    "duration": 3600,
    "size": 52428800,
    "uploaded_at": "2026-06-01T10:15:00"
  },
  "processing_status": "completed",
  "transcript": {
    "id": "uuid",
    "segments": [
      {
        "speaker": "SPEAKER_00",
        "start": 0.0,
        "end": 14.5,
        "text": "Oke selamat pagi semua, kita mulai sprint planning."
      }
    ]
  },
  "summary": {
    "id": "uuid",
    "tldr": "Sprint planning membahas 3 task utama untuk minggu ini.",
    "decisions": ["Deploy ke staging hari Rabu", "Code freeze Jumat sore"],
    "topics": ["Review backlog", "Estimasi task", "Assign task"]
  },
  "action_items": [
    {
      "id": "uuid",
      "task": "Bikin endpoint upload recording",
      "assignee": {
        "id": "uuid",
        "name": "Audi",
        "email": "audi@email.com"
      },
      "due_date": "2026-06-05",
      "status": "open"
    }
  ]
}
```

### PATCH /meetings/:id
Update meeting. Hanya organizer yang bisa.

**Request (semua field optional):**
```json
{
  "title": "Sprint Planning Week 3 - Updated",
  "scheduled_at": "2026-06-01T10:00:00",
  "location": "Meeting Room B",
  "description": "...",
  "agenda_text": "..."
}
```
**Response 200:** sama dengan GET /meetings/:id

### DELETE /meetings/:id
Hapus meeting. Hanya organizer yang bisa.

**Response 204:** no content

### GET /meetings/search
Search meeting berdasarkan judul, summary, atau action item.

**Query params:**
- `q` (required): keyword pencarian
- `page` (default: 1)
- `limit` (default: 10)

**Response 200:** sama dengan GET /meetings

---

## Recording

### POST /meetings/:id/recording
Upload file rekaman. Hanya organizer yang bisa. Trigger pipeline ML otomatis.

**Request:** multipart/form-data
- `file`: file audio (mp3, mp4, wav, m4a, max 200MB)

**Response 202:**
```json
{
  "id": "uuid",
  "file_url": "recordings/uuid/audio.mp3",
  "duration": null,
  "size": 52428800,
  "uploaded_at": "2026-06-01T10:15:00",
  "processing_status": "queued"
}
```

### GET /meetings/:id/recording/status
Cek status processing pipeline ML.

**Response 200:**
```json
{
  "processing_status": "transcribing",
  "steps": {
    "upload": "completed",
    "transcribe": "in_progress",
    "diarize": "pending",
    "extract_summary": "pending",
    "extract_action_items": "pending",
    "send_email": "pending"
  },
  "error": null
}
```

Status values: `queued`, `transcribing`, `diarizing`, `extracting`, `sending_email`, `completed`, `failed`

### DELETE /meetings/:id/recording
Hapus file rekaman. Hanya organizer yang bisa. Hapus juga transcript, summary, action item terkait.

**Response 204:** no content

---

## Check-in (Public, No Auth)

### GET /check-in/:token
Validasi token, tampilkan info meeting untuk halaman check-in.

**Response 200:**
```json
{
  "meeting_title": "Sprint Planning Week 3",
  "scheduled_at": "2026-06-01T09:00:00",
  "location": "Meeting Room A",
  "participant_name": "Helena",
  "already_checked_in": false
}
```
**Response 404:** token tidak valid atau expired

### POST /check-in/:token/confirm
Konfirmasi kehadiran peserta.

**Response 200:**
```json
{
  "message": "Kehadiran berhasil dikonfirmasi",
  "participant_name": "Helena",
  "meeting_title": "Sprint Planning Week 3"
}
```

---

## Attendance

### PATCH /meetings/:id/participants/:participant_id/attendance
Update status kehadiran secara manual. Hanya organizer yang bisa.

**Request:**
```json
{
  "status": "hadir"
}
```
Status values: `pending`, `hadir`, `tidak_hadir`

**Response 200:**
```json
{
  "participant_id": "uuid",
  "name": "Helena",
  "status": "hadir",
  "method": "manual"
}
```

---

## Action Items

### PATCH /action-items/:id
Update status action item. Organizer bisa update semua, peserta hanya bisa update miliknya.

**Request:**
```json
{
  "status": "done"
}
```
**Response 200:**
```json
{
  "id": "uuid",
  "task": "Bikin endpoint upload recording",
  "status": "done"
}
```

### GET /me/action-items
List semua action item yang di-assign ke user yang login, lintas meeting.

**Query params:**
- `status` (optional): `open`, `done`

**Response 200:**
```json
{
  "items": [
    {
      "id": "uuid",
      "task": "Bikin endpoint upload recording",
      "due_date": "2026-06-05",
      "status": "open",
      "meeting": {
        "id": "uuid",
        "title": "Sprint Planning Week 3",
        "scheduled_at": "2026-06-01T09:00:00"
      }
    }
  ]
}
```

---

## Error Format

Semua error menggunakan format yang sama:

```json
{
  "detail": "Pesan error yang menjelaskan masalah"
}
```

HTTP status codes yang dipakai:
- `400` Bad Request (input tidak valid)
- `401` Unauthorized (token tidak ada atau expired)
- `403` Forbidden (tidak punya permission)
- `404` Not Found
- `413` Payload Too Large (file terlalu besar)
- `422` Unprocessable Entity (validasi Pydantic gagal)
- `500` Internal Server Error