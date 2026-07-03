# Plan: Fitur Tandai Rapat Selesai

## Context
Organizer tidak bisa menandai rapat sebagai selesai dari UI. Akibatnya peserta yang terlambat masih bisa check-in setelah rapat berakhir. Perlu tombol "Tandai Selesai" di halaman detail rapat yang sekaligus mengunci presensi.

Model `Meeting` sudah punya `status` (`scheduled`/`completed`/`cancelled`) dan `attendance_locked` (bool). Logika lock attendance sudah ada di `services/checkin.py`. Tinggal expose via endpoint baru dan buat UI-nya.

---

## Backend

### File 1: `backend/app/services/meeting.py`
Tambah fungsi `complete_meeting()` — gabungkan set status + lock attendance:

```python
def complete_meeting(db: Session, meeting_id: uuid.UUID, user_id: uuid.UUID) -> Meeting:
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting tidak ditemukan")
    if meeting.organizer_id != user_id:
        raise HTTPException(status_code=403, detail="Hanya organizer yang bisa menyelesaikan rapat")
    if meeting.status == MeetingStatus.completed:
        raise HTTPException(status_code=400, detail="Rapat sudah selesai")

    meeting.status = MeetingStatus.completed
    meeting.attendance_locked = True

    for p in meeting.participants:
        if p.role == ParticipantRole.peserta:
            if p.attendance:
                if p.attendance.status == AttendanceStatus.pending:
                    p.attendance.status = AttendanceStatus.tidak_hadir
            else:
                db.add(Attendance(
                    participant_id=p.id,
                    status=AttendanceStatus.tidak_hadir,
                    method=AttendanceMethod.manual,
                ))

    db.commit()
    db.refresh(meeting)
    return meeting
```

Import tambahan yang mungkin belum ada di file: `ParticipantRole`, `Attendance`, `AttendanceStatus`, `AttendanceMethod` — cek dan tambahkan seperlunya.

### File 2: `backend/app/routers/meetings.py`
Tambah endpoint setelah `update_meeting`:

```python
@router.patch("/{meeting_id}/complete", response_model=MeetingDetail)
def complete_meeting(
    meeting_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return meeting_service.complete_meeting(db, meeting_id=meeting_id, user_id=current_user.id)
```

---

## Frontend

### File 3: `frontend/lib/api.ts`
Tambah fungsi:

```typescript
export const completeMeeting = async (id: string) => {
  const response = await api.patch(`/meetings/${id}/complete`);
  return response.data;
};
```

### File 4: `frontend/app/(main)/meetings/[id]/page.tsx`
**Import tambahan:**
```typescript
import { completeMeeting } from "@/lib/api";
import { CheckCircle } from "lucide-react";
```

**State baru:**
```typescript
const [isCompleting, setIsCompleting] = useState(false);
```

**Handler baru:**
```typescript
const handleCompleteMeeting = async () => {
  setIsCompleting(true);
  try {
    await completeMeeting(id);
    toast.success("Rapat ditandai selesai. Presensi dikunci.");
    router.refresh();
  } catch {
    toast.error("Gagal menyelesaikan rapat.");
  } finally {
    setIsCompleting(false);
  }
};
```

**Tombol** — taruh di samping "Edit Rapat", hanya tampil jika `isOrganizer && meeting.status === "scheduled"`.
Gunakan pola AlertDialog yang sama dengan tombol "Hapus Rapat":

```tsx
{isOrganizer && meeting.status === "scheduled" && (
  <AlertDialog>
    <AlertDialogTrigger asChild>
      <button className="text-xs font-semibold text-emerald-600 border border-emerald-200 px-4 py-2 rounded-xl hover:bg-emerald-50 transition flex items-center gap-1.5">
        <CheckCircle size={13} /> Tandai Selesai
      </button>
    </AlertDialogTrigger>
    <AlertDialogContent className="bg-white border border-slate-200 text-slate-900">
      <AlertDialogHeader>
        <AlertDialogTitle>Tandai Rapat Selesai?</AlertDialogTitle>
        <AlertDialogDescription className="text-slate-500">
          Presensi akan dikunci. Peserta yang belum hadir otomatis ditandai "Tidak Hadir". Tindakan ini tidak dapat dibatalkan.
        </AlertDialogDescription>
      </AlertDialogHeader>
      <AlertDialogFooter>
        <AlertDialogCancel className="bg-transparent border border-slate-200 text-slate-700 hover:bg-slate-50">
          Batalkan
        </AlertDialogCancel>
        <AlertDialogAction
          onClick={handleCompleteMeeting}
          disabled={isCompleting}
          className="bg-emerald-600 hover:bg-emerald-500 text-white border-0 disabled:opacity-50"
        >
          {isCompleting ? "Memproses..." : "Ya, Selesaikan"}
        </AlertDialogAction>
      </AlertDialogFooter>
    </AlertDialogContent>
  </AlertDialog>
)}
```

---

## Verification
- Buka detail rapat berstatus `scheduled` sebagai organizer → tombol "Tandai Selesai" muncul
- Klik → konfirmasi → status berubah `completed`, `attendance_locked = true`
- Peserta yang belum check-in statusnya berubah jadi `tidak_hadir`
- Buka magic link check-in → dapat error 403 "Absensi sudah ditutup"
- Rapat sudah `completed` → tombol tidak muncul lagi
