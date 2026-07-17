# Handoff untuk Backend — Presensi Mandiri (Self Check-in)

**Tanggal:** 2026-07-14
**Branch:** `frontend`
**Fitur:** Peserta bisa presensi lewat akun mereka sendiri (login), bukan cuma lewat magic link di email.

---

## Yang Harus Dikerjakan BE

### 1. [Blocker — satu-satunya yang menghalangi fitur ini jalan] Izinkan peserta melihat `checkin_token` miliknya sendiri

**Lokasi:** `backend/app/routers/meetings.py`, fungsi `get_meeting` (baris 62-75)

```python
@router.get("/{meeting_id}", response_model=MeetingDetail)
def get_meeting(
    meeting_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    meeting = meeting_service.get_meeting(db, meeting_id=meeting_id, user_id=current_user.id)
    detail = MeetingDetail.model_validate(meeting)
    if meeting.organizer_id != current_user.id:
        # checkin_token adalah magic link milik masing-masing peserta — jangan
        # bocor ke peserta lain, hanya organizer yang boleh melihatnya.
        for participant in detail.participants:
            participant.checkin_token = None
    return detail
```

**Masalahnya:** logic ini benar untuk mencegah peserta A melihat token peserta B (itu memang harus tetap diblokir — token itu setara magic link, siapa pun yang pegang bisa check-in atas nama peserta itu). Tapi loop-nya mengosongkan token **semua** peserta tanpa kecuali, termasuk token milik `current_user` sendiri. Akibatnya peserta yang login lewat akun sendiri tidak pernah bisa lihat token miliknya sendiri lewat endpoint ini.

**Fix yang diminta:** kecualikan entry milik `current_user` sendiri dari pengosongan. Kira-kira begini (silakan sesuaikan gaya kode BE):

```python
if meeting.organizer_id != current_user.id:
    for participant in detail.participants:
        if participant.email != current_user.email:
            participant.checkin_token = None
```

(Pakai `email` karena itu yang tersedia di `ParticipantResponse`; kalau ada field yang lebih pas seperti `user_id`, silakan pakai itu — yang penting perbandingannya terhadap identitas `current_user`, bukan wholesale null semua.)

**Kenapa ini aman:** token yang dibalikkan cuma milik requester sendiri — tetap tidak ada peserta lain yang tokennya bocor. Behavior existing (organizer bisa lihat semua token, non-organizer tidak bisa lihat token orang lain) tidak berubah sama sekali.

**Cara FE pakai token ini:** setelah token ini kebuka, FE akan panggil endpoint yang **sudah ada** dan **tidak perlu diubah**, `POST /check-in/{token}/confirm` (`backend/app/routers/checkin.py`), persis seperti yang dipakai portal magic-link sekarang. **Tidak ada endpoint baru yang perlu dibuat.**

---

### 2. [Sudah dicek, bukan tugas BE] Endpoint alternatif tidak ada dan memang tidak dibutuhkan
Sempat dicek juga apakah `PATCH /meetings/{meeting_id}/participants/{participant_id}/attendance` (`update_attendance_manual` di `backend/app/services/checkin.py`) bisa dipakai peserta buat presensi diri sendiri — ternyata endpoint itu hard-required organizer (`meeting.organizer_id != organizer_id → 403`), jadi memang bukan jalur yang dipakai FE. Tidak perlu diubah, cukup fix #1 di atas.

---

## Konteks FE (biar BE paham kenapa ini dibutuhkan)

- Card baru "Presensi Saya" di halaman detail rapat (`frontend/app/(main)/meetings/[id]/page.tsx`), muncul kalau user yang login adalah peserta (bukan organizer) rapat tersebut
- Dapat token dari `myParticipant.checkin_token` (hasil `meeting.participants.find(p => p.email === currentUserEmail)`)
- Kalau token ada → tombol "Check In Sekarang" memanggil `POST /check-in/{token}/confirm` lewat hook `useSelfCheckIn` (`frontend/hooks/useMeeting.ts`)
- Kalau token `null` (kondisi saat ini, sebelum fix #1) → tombol menampilkan toast `"Presensi mandiri belum tersedia untuk akunmu..."` alih-alih diam saja

**Root cause ini sudah dikonfirmasi lewat testing langsung** (curl pakai JWT milik peserta sendiri, bukan cuma organizer) — bukan race condition atau caching, murni logic redaksi di atas.

## Cara Verifikasi Setelah Fix
1. Login sebagai organizer, buat rapat, undang 1 peserta yang sudah punya akun
2. Login sebagai peserta itu di tab/browser lain, buka rapat yang sama
3. `GET /meetings/{id}` — punya peserta itu sendiri harus tampil `checkin_token` berisi string (bukan `null`), sementara `checkin_token` milik peserta LAIN (kalau ada lebih dari satu peserta) tetap harus `null`
4. Di UI, card "Presensi Saya" → klik "Check In Sekarang" → status berubah jadi "Kehadiran Tercatat", dan di sisi organizer STATUS KEHADIRAN peserta itu berubah jadi "Hadir"

Begitu ini di-deploy, FE tidak perlu ada perubahan tambahan lagi — kabari saja kalau sudah live supaya bisa langsung diverifikasi ujung-ke-ujung.
