# Plan: Participant Portal + Attendance Lock

**Status:** READY TO IMPLEMENT  
**Owner:** BE (Audi) + FE (Helena) | ML: tidak ada perubahan

---

## Context

Tiga masalah yang diselesaikan:
1. Magic link hanya dipakai sekali untuk check-in → jadikan **portal permanen** (notulen + action items)
2. Email notulen kirim konten lengkap yang redundan → cukup kirim **link portal**
3. Attendance window terlalu panjang (48 jam fallback) dan bergantung pada aksi manusia → ganti dengan **`duration_minutes`** sebagai mekanisme unconditional

**Keputusan attendance lock:**
- Primary: `scheduled_at + duration_minutes + 30 menit grace` — dihitung dinamis, otomatis bergeser saat reschedule
- Override opsional: recording diupload → set `attendance_locked_at = now()`
- Token portal tidak pernah expire — peserta bisa akses notulen & action items kapanpun

---

## Yang Sudah Ada (Tidak Perlu Diubah)

Dari commit "checkin portal feature added":
- `CheckinPageResponse` sudah include `summary`, `action_items`, `processing_status`, `attendance_locked`
- `services/checkin.py` sudah query Recording, Summary, ActionItem dan punya `_is_attendance_locked()`
- `PATCH /check-in/{token}/action-items/{id}` sudah ada di router
- Token tidak dicek expiry di `get_checkin_info()`

---

## Backend — Audi

### 1. `backend/app/models/meeting.py`
Tambah field:
```python
duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
```

### 2. Migration baru
```bash
docker compose exec backend-api alembic revision --autogenerate -m "add duration_minutes to meetings"
make migrate
```
Ikuti pola CLAUDE.md: buat ENUM dengan `checkfirst=True` di awal jika ada enum baru (di sini tidak ada enum baru, migration straightforward).

### 3. `backend/app/schemas/meeting.py`
Tambah `duration_minutes` ke:
- `MeetingCreate` → `duration_minutes: int = 60`
- `MeetingUpdate` → `duration_minutes: int | None = None`
- `MeetingResponse` → `duration_minutes: int`

### 4. `backend/app/services/checkin.py`
Update `_is_attendance_locked()`:
```python
def _is_attendance_locked(meeting: Meeting) -> bool:
    if meeting.attendance_locked_at:
        return datetime.now(timezone.utc) > meeting.attendance_locked_at
    grace = timedelta(minutes=30)
    scheduled_end = meeting.scheduled_at + timedelta(minutes=meeting.duration_minutes)
    return datetime.now(timezone.utc) > scheduled_end + grace
```
Dihitung dinamis → reschedule otomatis bergeser tanpa perlu update field lain.

### 5. `backend/app/services/recording.py`
Di fungsi upload recording, setelah recording disimpan ke DB, set early lock:
```python
meeting.attendance_locked_at = datetime.now(timezone.utc)
db.commit()
```
Ini override opsional — sinyal kuat bahwa meeting sudah selesai saat rekaman diupload.

### 6. `backend/app/services/email.py`
Sederhanakan `send_notulen_email()` — hapus parameter konten, ganti dengan `checkin_url`:
```python
def send_notulen_email(
    recipient_email: str,
    recipient_name: str,
    meeting_title: str,
    scheduled_at: datetime,
    checkin_url: str,           # ← ganti semua parameter konten dengan ini
    meeting_id: uuid.UUID,
    db: Session,
) -> None:
```
Email body: notifikasi singkat + link portal saja. Tidak ada summary/decisions/action items di email.

### 7. `backend/app/tasks/process_recording.py`
Update loop pengiriman email (sekitar baris 170–189):
```python
for p in participants:
    checkin_url = f"{settings.APP_BASE_URL}/check-in/{p.invitation.token}"
    send_notulen_email(
        recipient_email=p.email,
        recipient_name=p.user.name if p.user else p.email,
        meeting_title=meeting.title,
        scheduled_at=meeting.scheduled_at,
        checkin_url=checkin_url,
        meeting_id=uuid.UUID(meeting_id),
        db=db,
    )
```

---

## Frontend — Helena

### 1. `frontend/lib/api.ts`
Tambah fungsi baru:
```typescript
export const updateCheckinActionItem = (
  token: string,
  actionItemId: string,
  status: "open" | "done"
) => api.patch(`/check-in/${token}/action-items/${actionItemId}`, { status }).then(r => r.data);
```
Update tipe `MeetingInfo` (interface lokal di check-in page) sesuai `CheckinPageResponse` dari BE yang sudah include `summary`, `action_items`, `processing_status`, `attendance_locked`.

### 2. Form Create Meeting — tambah field Durasi
File: form/page create meeting yang ada

Tambah dropdown di sebelah field waktu mulai:
```
Waktu Mulai:  [date/time picker]
Durasi:       [Select: 30 / 60 / 90 / 120 / 180 / 240 menit]  ← baru, default 60
```
Kirim `duration_minutes` sebagai bagian dari payload `POST /meetings`.

### 3. Form Edit Meeting — tambah field Durasi
Tambah dropdown Durasi yang sama. Kirim `duration_minutes` di payload `PATCH /meetings/:id`.

### 4. `frontend/app/check-in/[token]/page.tsx`
Redesign total dari single-action form menjadi portal 3 kartu vertikal.

**Header halaman** (selalu tampil setelah token valid):
- Nama peserta + judul meeting + waktu + lokasi

**Kartu 1 — Presensi**
| State | Tampilan |
|---|---|
| `attendance_locked = false` + belum check-in | Tombol "Check In Sekarang" |
| `already_checked_in = true` | Badge hijau "Hadir ✓" |
| `attendance_locked = true` + belum check-in | "Presensi sudah ditutup" |
| `attendance_locked = true` + sudah check-in | Badge hijau "Hadir ✓" |

Setelah check-in berhasil: halaman **tidak redirect**, tetap tampil semua kartu lain.

**Kartu 2 — Notulen**
| State | Tampilan |
|---|---|
| `processing_status = null` | "Rekaman belum diupload" |
| Status in progress | Progress indicator + label tahap saat ini |
| `processing_status = completed` + ada summary | `tldr`, decisions (list), topics (pills) |
| `processing_status = failed` | "Pemrosesan rekaman gagal" |

**Kartu 3 — Action Items**
- List `response.action_items` milik peserta ini
- Tiap item: nama task, due_date (jika ada), toggle button open ↔ done
- Toggle panggil `updateCheckinActionItem(token, id, newStatus)`, update state lokal setelah response
- Kosong → "Tidak ada action item untuk Anda di rapat ini"

**Update error state:** Ubah pesan "sudah kadaluarsa" → "Link undangan tidak valid" (token tidak expire).

---

## Urutan Implementasi

**Backend (Audi) — berurutan:**
1. Model + migration (`duration_minutes`)
2. Schema meeting (MeetingCreate, MeetingUpdate, MeetingResponse)
3. Service checkin — update `_is_attendance_locked()`
4. Service recording — set `attendance_locked_at` saat upload
5. Service email — sederhanakan `send_notulen_email()`
6. Task process_recording — update pemanggilan email

**Frontend (Helena) — bisa paralel setelah BE selesai nomor 1–3:**
1. `api.ts` — tambah `updateCheckinActionItem` + update types
2. Form create meeting — tambah dropdown durasi
3. Form edit meeting — tambah dropdown durasi
4. Halaman check-in — redesign jadi 3 kartu

---

## Verifikasi End-to-End

1. Buat meeting durasi 30 menit → cek `duration_minutes` tersimpan di DB
2. Buka magic link sebelum `scheduled_at + 60 menit` → tombol check-in aktif → check-in berhasil
3. Tunggu `scheduled_at + 30 menit + 30 menit grace` → buka magic link → tombol check-in berubah "ditutup"
4. Reschedule meeting → konfirmasi lock otomatis bergeser ke jadwal baru
5. Upload recording → cek `attendance_locked_at` ter-set di DB → portal masih bisa diakses, check-in terkunci
6. Setelah ML selesai → kartu Notulen tampil summary + decisions
7. Toggle action item → refresh halaman → status persisten
8. Cek Mailhog setelah ML selesai → email hanya berisi link portal, tidak ada konten lengkap
