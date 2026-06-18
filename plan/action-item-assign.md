# Feature: Manual Assign Action Items ke Peserta Rapat

**Status:** FE selesai — menunggu implementasi BE  
**Owner:** BE (3 file) · FE sudah selesai · ML tidak ada perubahan  
**Branch target:** `feature/backend-assign-action-item`

---

## Konteks

Model `ActionItem` sudah punya kolom `assignee_participant_id` (FK ke `meeting_participants`) sejak schema awal, dan ML pipeline sudah mencoba auto-assign saat transcript diproses. Tapi endpoint `PATCH /action-items/{id}` saat ini hanya menerima field `status` — tidak ada cara bagi organizer untuk memperbaiki assignment yang salah atau mengisi yang kosong.

**FE sudah selesai dibangun:**
- Dropdown assign di `ActionItemList.tsx` (native select, stopPropagation, pre-select by participant ID)
- `updateActionItem` di `api.ts` sudah kirim `assignee_participant_id` dalam payload
- `handleAssignTask` + `participantOptions` sudah terpasang di `/meetings/[id]/page.tsx`
- FE **hanya butuh 3 perubahan BE di bawah** untuk bekerja end-to-end

**Known behavior tanpa perubahan BE:** PATCH dikirim dengan `assignee_participant_id`, Pydantic v2 diam-diam mengabaikan field yang tidak dikenal (HTTP 200 tapi tidak tersimpan). Tidak ada error, tapi assign tidak persist.

---

## Perubahan BE yang Diperlukan

### 1. Extend `ActionItemUpdateRequest`

**File:** `backend/app/schemas/action_item.py` — baris 51-52

**Saat ini:**
```python
class ActionItemUpdateRequest(BaseModel):
    status: ActionItemStatus
```

**Ganti menjadi:**
```python
class ActionItemUpdateRequest(BaseModel):
    status: Optional[ActionItemStatus] = None
    assignee_participant_id: Optional[UUID] = None
```

> Kedua field dibuat `Optional` agar satu PATCH bisa update hanya `status`, hanya `assigneeParticipantId`, atau keduanya sekaligus. Caller lama yang kirim `{"status": "done"}` tetap berfungsi tanpa perubahan.

---

### 2. Update service `update_action_item`

**File:** `backend/app/services/action_item.py` — fungsi `update_action_item` (baris 10-30)

**Ganti seluruh fungsi menjadi:**
```python
def update_action_item(db: Session, action_item_id: uuid.UUID, user_id: uuid.UUID, data: ActionItemUpdateRequest) -> ActionItem:
    action_item = db.query(ActionItem).filter(ActionItem.id == action_item_id).first()
    if not action_item:
        raise HTTPException(status_code=404, detail="Action item not found")

    meeting = db.query(Meeting).filter(Meeting.id == action_item.meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    update_data = data.model_dump(exclude_unset=True)
    is_organizer = meeting.organizer_id == user_id

    # Update status: organizer ATAU assignee saat ini (aturan lama, tidak berubah)
    if "status" in update_data:
        is_current_assignee = (
            action_item.assignee_participant is not None
            and action_item.assignee_participant.user_id == user_id
        )
        if not (is_organizer or is_current_assignee):
            raise HTTPException(status_code=403, detail="Not authorized to update this action item")
        action_item.status = update_data["status"]

    # Update assignee: ORGANIZER ONLY
    if "assignee_participant_id" in update_data:
        if not is_organizer:
            raise HTTPException(status_code=403, detail="Hanya organizer yang bisa assign action item")
        new_assignee_id = update_data["assignee_participant_id"]
        if new_assignee_id is not None:
            participant = db.query(MeetingParticipant).filter(
                MeetingParticipant.id == new_assignee_id,
                MeetingParticipant.meeting_id == meeting.id,
            ).first()
            if not participant:
                raise HTTPException(status_code=400, detail="Participant bukan anggota rapat ini")
        action_item.assignee_participant_id = new_assignee_id

    db.commit()
    db.refresh(action_item)
    return action_item
```

**Aturan validasi:**
- `status` update: organizer ATAU participant yang sedang di-assign (tidak berubah dari sebelumnya)
- `assignee_participant_id` update: **organizer only**
- Cross-meeting guard: participant yang di-assign wajib `MeetingParticipant` dari meeting yang sama → return `400` bukan `403`
- Unassign: kirim `assignee_participant_id: null` secara eksplisit (kolom nullable, aman)
- **Tidak perlu migration** — kolom sudah ada sejak `9a7befed844a_initial_schema.py`

---

### 3. Fix nested `assignee` di `MeetingDetail`

**File:** `backend/app/schemas/meeting.py` — list comprehension `action_items` di `MeetingDetail.extract_fields` (baris 150-158)

**Saat ini** hanya mengembalikan `assignee_participant_id` mentah. Akibatnya nama assignee (dari ML maupun manual) tidak pernah tampil di halaman detail meeting — selalu "Belum di-assign".

**Ganti blok action_items menjadi:**
```python
action_items = [
    {
        "id": str(ai.id),
        "task": ai.task,
        "assignee_participant_id": str(ai.assignee_participant_id) if ai.assignee_participant_id else None,
        "assignee": (
            {
                "id": str(ai.assignee_participant.user.id),
                "name": ai.assignee_participant.user.name,
                "email": ai.assignee_participant.user.email,
            }
            if ai.assignee_participant and ai.assignee_participant.user
            else None
        ),
        "due_date": ai.due_date.isoformat() if ai.due_date else None,
        "status": ai.status.value if hasattr(ai.status, "value") else ai.status,
    }
    for ai in (getattr(data, "action_items", None) or [])
]
```

> Tetap pertahankan `assignee_participant_id` di response (FE butuh ini untuk pre-select dropdown). `assignee` object (`id`, `name`, `email`) adalah bonus untuk display di view non-organizer. Jika participant belum registrasi akun (`user` null), `assignee` tetap `null` — sudah ditangani di FE.

> ⚠️ Perubahan ini juga memicu lazy-load `ai.assignee_participant.user` per action item. Rekomendasikan digabung dengan fix eager loading dari `IMPROVEMENTS.md` item #6 (`joinedload(Meeting.action_items).joinedload(ActionItem.assignee_participant).joinedload(MeetingParticipant.user)`) dalam PR yang sama untuk menghindari N+1.

---

## ML — Tidak Ada Perubahan

`extract_action_items()` dan kontrak skema ML (frozen per CLAUDE.md) tidak disentuh. ML hanya menulis assignee sekali saat transcript diproses; fitur ini adalah lapisan koreksi manual di atasnya.

---

## Priority & Effort

| # | Item | Impact | Effort | Blocker untuk FE? |
|---|------|--------|--------|--------------------|
| 1 | Extend `ActionItemUpdateRequest` | Tinggi | Sangat Rendah | ✅ Ya |
| 2 | Update service authorization | Tinggi | Rendah | ✅ Ya |
| 3 | Fix `MeetingDetail` nested assignee | Medium | Rendah | Partial (FE punya workaround via participant lookup) |
