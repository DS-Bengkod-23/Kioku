# MeetMate — Improvement Backlog

Daftar improvement yang teridentifikasi setelah fungsionalitas dasar berjalan.
Diurutkan dari yang paling berdampak ke user.

---

## UX / Frontend

### 1. Polling tidak restart setelah refresh halaman
**File:** `frontend/app/(main)/meetings/[id]/page.tsx`  
**Masalah:** `pollingEnabled` selalu mulai dari `false`. Kalau user refresh saat ML masih processing, status beku.  
**Fix:** Auto-enable polling saat mount jika `meeting.processing_status` masih dalam state aktif (`transcribing`, `diarizing`, `extracting`, `queued`).

```typescript
// Tambah useEffect setelah data meeting loaded
useEffect(() => {
  if (["queued", "transcribing", "diarizing", "extracting", "sending_email"].includes(meeting?.processing_status)) {
    setPollingEnabled(true);
  }
}, [meeting?.processing_status]);
```

---

### 2. Due date action items default ke "2099-12-31"
**File:** `frontend/app/(main)/meetings/[id]/page.tsx` (baris mapping actionItems)  
**Masalah:** `dueDate: item.due_date || "2099-12-31"` — menampilkan tanggal aneh di UI saat ML tidak set due date.  
**Fix:** Biarkan `undefined` agar komponen menampilkan "–".

```typescript
dueDate: item.due_date ?? undefined,
```

---

### 3. Priority action items hardcoded "Sedang"
**File:** `frontend/app/(main)/meetings/[id]/page.tsx`  
**Masalah:** Semua action item selalu "Sedang", tidak ada variasi.
**Option A:** Tambahkan field `priority` ke model ActionItem di backend + ML extraction.  
**Option B (cepat):** Set priority berdasarkan due_date — overdue = "Tinggi", dalam 3 hari = "Sedang", lainnya = "Rendah".

---

### 4. Manual assignment action items ke peserta
**Plan file:** `plan/action-item-assign.md`  
**Status:** ✅ FE selesai — menunggu 3 perubahan BE (spek lengkap di plan file).  
**Scope:** 3 backend — tidak perlu koordinasi ML. Jangan merge FE ke `main` sebelum BE rilis.

---

### 5. Tidak bisa edit task / due date action item secara manual
**Masalah:** Hanya bisa toggle done/open. Tidak ada UI untuk ubah teks task atau tanggal.  
**Fix:** Tambah `PUT /action-items/{id}` endpoint (atau extend PATCH) + inline edit UI di `ActionItemList.tsx`.

---

## Backend

### 6. N+1 queries di `get_meeting`
**File:** `backend/app/services/meeting.py`  
**Masalah:** `db.query(Meeting).filter(...)` tanpa `joinedload` — setiap akses ke relasi (`participants`, `action_items`, `assignee_participant.user`) picu query terpisah.  
**Fix:** Tambahkan eager loading:

```python
from sqlalchemy.orm import joinedload

meeting = db.query(Meeting).options(
    joinedload(Meeting.participants).joinedload(MeetingParticipant.user),
    joinedload(Meeting.action_items).joinedload(ActionItem.assignee_participant).joinedload(MeetingParticipant.user),
    joinedload(Meeting.transcript),
    joinedload(Meeting.summary),
).filter(Meeting.id == meeting_id).first()
```

---

### 7. Tidak bisa tambah/hapus peserta setelah rapat dibuat
**Masalah:** Tidak ada endpoint untuk update participant list post-creation.  
**Fix:** Tambah `POST /meetings/{id}/participants` dan `DELETE /meetings/{id}/participants/{participant_id}`.

---

## Pipeline / Reliability

### 8. Status Celery misleading saat pipeline gagal
**File:** `backend/app/tasks/process_recording.py`  
**Masalah:** `_mark_failed()` + `return` membuat task tampak "succeeded" di Celery, padahal recording di-mark failed di DB. Sulit di-monitor.  
**Fix:** Raise exception khusus alih-alih `return`, agar Celery mencatat task sebagai failed.

```python
class MLPipelineError(Exception):
    pass

# Ganti semua `return` setelah `_mark_failed()`
raise MLPipelineError("Transcribe failed: ...")
```

---

## Priority Ranking

| # | Item | Impact | Effort | Owner |
|---|------|--------|--------|-------|
| 1 | Polling restart after refresh | Tinggi | Rendah | FE |
| 2 | Due date "2099-12-31" fix | Medium | Rendah | FE |
| 3 | Manual assign action items | Tinggi | Medium | BE + FE |
| 4 | N+1 queries fix | Medium | Rendah | BE |
| 5 | Celery status misleading | Medium | Rendah | BE |
| 6 | Edit task / due date | Medium | Tinggi | BE + FE |
| 7 | Tambah/hapus peserta | Rendah | Tinggi | BE + FE |
| 8 | Priority action items | Rendah | Medium | BE + FE + ML |