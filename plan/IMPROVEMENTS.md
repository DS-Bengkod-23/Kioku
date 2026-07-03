# MeetMate — Improvement Backlog

Daftar improvement yang teridentifikasi setelah fungsionalitas dasar berjalan.
Diurutkan dari yang paling berdampak ke user.

---

## UX / Frontend

### 1. Polling tidak restart setelah refresh halaman — ✅ SELESAI
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

### 2. Due date action items default ke "2099-12-31" — ✅ SELESAI
**File:** `frontend/app/(main)/meetings/[id]/page.tsx` (baris mapping actionItems)  
**Masalah:** `dueDate: item.due_date || "2099-12-31"` — menampilkan tanggal aneh di UI saat ML tidak set due date. Akar masalahnya ternyata di backend: `tasks/process_recording.py` membaca `item.due_date` padahal field ML-nya `due_date_text` — sudah diperbaiki juga, jadi due date hasil AI sekarang benar-benar terisi kalau LLM menyebutkannya.  
**Fix:** `dueDate: item.due_date ?? undefined` — sudah diterapkan konsisten di `meetings/[id]/page.tsx` dan `action-items/page.tsx`.

---

### 3. Priority action items hardcoded "Sedang" — ✅ SELESAI
**File:** `frontend/app/(main)/meetings/[id]/page.tsx`  
**Fix:** Opsi B diterapkan (priority dihitung dari due_date), dan dibuat konsisten dengan `isDateOverdue()` lewat helper `daysUntil()` di `lib/utils.ts` supaya badge status & priority tidak lagi bisa berkontradiksi di dekat batas hari.

---

### 4. Manual assignment action items ke peserta — ✅ SELESAI
**Plan file:** `plan/action-item-assign.md`  
**Status:** BE + FE selesai, `POST /meetings/{id}/action-items` dan `PATCH /action-items/{id}` (assign) sudah berfungsi penuh.

---

### 5. Tidak bisa edit task / due date action item secara manual
**Masalah:** Hanya bisa toggle done/open. Tidak ada UI untuk ubah teks task atau tanggal.  
**Fix:** Tambah `PUT /action-items/{id}` endpoint (atau extend PATCH) + inline edit UI di `ActionItemList.tsx`.

---

## Backend

### 6. N+1 queries di `get_meeting` — ✅ SELESAI
**File:** `backend/app/services/meeting.py`  
**Masalah:** `db.query(Meeting).filter(...)` tanpa `joinedload` — setiap akses ke relasi (`participants`, `action_items`, `assignee_participant.user`) picu query terpisah.  
**Fix diterapkan** (juga di `get_meetings`/`search_meetings` untuk list endpoint):

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

### 7. Tidak bisa tambah/hapus peserta setelah rapat dibuat — ✅ SELESAI (stale, sudah ada)
**Status:** `MeetingUpdate` schema sudah punya `participant_emails`, dan `update_meeting()` (`services/meeting.py`) sudah mengimplementasikan diff peserta (tambah/hapus + kirim undangan baru) dengan benar. Endpoint terpisah `POST .../participants` tidak jadi dibuat — cukup lewat `PATCH /meetings/{id}`.

---

## Pipeline / Reliability

### 8. Status Celery misleading saat pipeline gagal — ✅ SELESAI
**File:** `backend/app/tasks/process_recording.py`  
**Masalah:** `_mark_failed()` + `return` membuat task tampak "succeeded" di Celery, padahal recording di-mark failed di DB. Sulit di-monitor.  
**Fix diterapkan:** raise `MLPipelineError` alih-alih `return`, agar Celery mencatat task sebagai failed.

```python
class MLPipelineError(Exception):
    pass

# Ganti semua `return` setelah `_mark_failed()`
raise MLPipelineError("Transcribe failed: ...")
```

---

## Priority Ranking

| # | Item | Impact | Effort | Owner | Status |
|---|------|--------|--------|-------|--------|
| 1 | Polling restart after refresh | Tinggi | Rendah | FE | ✅ Selesai |
| 2 | Due date "2099-12-31" fix | Medium | Rendah | FE | ✅ Selesai |
| 3 | Manual assign action items | Tinggi | Medium | BE + FE | ✅ Selesai |
| 4 | N+1 queries fix | Medium | Rendah | BE | ✅ Selesai |
| 5 | Celery status misleading | Medium | Rendah | BE | ✅ Selesai |
| 6 | Edit task / due date | Medium | Tinggi | BE + FE | Belum |
| 7 | Tambah/hapus peserta | Rendah | Tinggi | BE + FE | ✅ Selesai |
| 8 | Priority action items | Rendah | Medium | BE + FE + ML | ✅ Selesai |