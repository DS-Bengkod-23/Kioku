# Handoff FE → BE — RSVP: kolom `reason` masih kurang

**Tanggal:** 2026-07-23
**Dari:** Helena (Frontend) · **Untuk:** Audi (Backend)
**Status:** RSVP inti udah jalan (`rsvp_status`, endpoint `PATCH /meetings/{id}/rsvp`) — makasih udah dikerjain duluan. Cuma ada **1 field kecil yang kelewat**: alasan/keterangan izin (`reason`) belum pernah ditambahin ke schema/model, jadi FE ngirim tapi kebuang di tengah jalan.

---

## Yang udah bener (dicek langsung dari kode, gak perlu diubah)

- Migration `f3a4b5c6d7e8_add_rsvp_status_to_participants.py` — kolom `rsvp_status` udah ada, enum-nya udah bener (`pending`/`akan_hadir`/`tidak_hadir`), dan udah ngikutin pola Alembic-enum yang didokumentasikan `CLAUDE.md` (`checkfirst=True` + `create_type=False`).
- `MeetingParticipant.rsvp_status` di model — bener.
- Endpoint `PATCH /meetings/{id}/rsvp` (`backend/app/routers/meetings.py:104-113`) — bener, guard 403/404-nya juga udah sesuai (cek langsung ke `MeetingParticipant` milik `current_user`, bukan lewat `checkin_token`).
- `submit_rsvp()` di `backend/app/services/meeting.py:270-287` — logic intinya bener.

## Yang kurang: field `reason`

FE (`frontend/lib/api.ts` → `submitRsvp()`) udah dari awal ngirim body `{ "response": "tidak_hadir", "reason": "sakit demam" }` ke endpoint di atas. Tapi karena `RsvpRequest` (schema) cuma declare field `response`, Pydantic diam-diam **buang field `reason`** yang gak dikenali — jadi gak pernah nyampe ke `submit_rsvp()`, gak pernah kesimpen, dan gak pernah balik ke FE. Makanya badge "Izin" muncul di tabel kehadiran organizer (karena `rsvp_status` udah bener), tapi keterangan alasannya selalu kosong.

### 1. Migration baru
Kolom `rsvp_reason` (nullable text) di `meeting_participants`:
```python
def upgrade() -> None:
    op.add_column(
        "meeting_participants",
        sa.Column("rsvp_reason", sa.Text(), nullable=True),
    )

def downgrade() -> None:
    op.drop_column("meeting_participants", "rsvp_reason")
```
(Gak butuh enum baru, jadi gak kena masalah Alembic-enum yang biasa — ini kolom teks biasa.)

### 2. Model — `backend/app/models/participant.py`
Tambah kolom di `MeetingParticipant`, sebelahan sama `rsvp_status` (~baris 38-40):
```python
rsvp_reason: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
```

### 3. Schema — `backend/app/schemas/meeting.py`
- `RsvpRequest` (baris 72-73) — tambah field opsional:
  ```python
  class RsvpRequest(BaseModel):
      response: Literal["akan_hadir", "tidak_hadir"]
      reason: Optional[str] = None
  ```
- `ParticipantResponse` (baris ~38-41) — tambah field biar keliatan balik ke FE (termasuk buat participant lain, bukan cuma diri sendiri, biar organizer bisa liat):
  ```python
  rsvp_status: str
  rsvp_reason: Optional[str] = None
  ```
  Dan di logic serialisasi-nya (baris ~57-69, tempat `rsvp_status` di-resolve dari `data.rsvp_status`) tambahin `"rsvp_reason": data.rsvp_reason` ke dict yang dibalikin.

### 4. Service — `backend/app/services/meeting.py`
`submit_rsvp()` (baris 270-287) — terima parameter baru & simpen:
```python
def submit_rsvp(db: Session, meeting_id: uuid.UUID, user_id: uuid.UUID, response: str, reason: str | None = None) -> Meeting:
    ...
    participant.rsvp_status = RsvpStatus(response)
    participant.rsvp_reason = reason if response == "tidak_hadir" else None
    db.commit()
    ...
```
(Kalau `response = "akan_hadir"`, `rsvp_reason` di-null-in — gak relevan buat konfirmasi hadir. FE juga cuma nampilin form alasan pas user pilih "Tidak bisa hadir".)

### 5. Router — `backend/app/routers/meetings.py`
`rsvp_meeting()` (baris 104-113) — teruskan `data.reason` ke service:
```python
meeting = meeting_service.submit_rsvp(db, meeting_id=meeting_id, user_id=current_user.id, response=data.response, reason=data.reason)
```

## Cara Verifikasi

1. Login sebagai participant, buka meeting yang `scheduled`, klik "Tidak bisa hadir", isi alasan "izin sakit", submit.
2. `GET /meetings/{id}` (sebagai organizer) — cek `participants[].rsvp_reason` untuk peserta itu balikin `"izin sakit"`, bukan `null`.
3. Di UI organizer (halaman detail meeting, tabel kehadiran) — klik badge "Izin" di baris peserta itu → keterangannya sekarang muncul ("Keterangan izin: izin sakit"), gak kosong lagi.
4. RSVP "akan_hadir" — pastiin `rsvp_reason` tetap `null` (gak ke-isi apa-apa yang gak relevan).

## Catatan
FE **gak perlu diubah sama sekali** buat ini — semua kode FE (kirim `reason`, tampilin `rsvp_reason`) udah dibangun dan nunggu field ini dari BE. Begitu 5 poin di atas selesai, langsung jalan tanpa perlu koordinasi ulang.
