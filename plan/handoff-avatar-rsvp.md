# Handoff FE → BE — Foto Profil & RSVP Konfirmasi Kehadiran

**Tanggal:** 2026-07-19
**Branch:** `frontend`
**Status:** FE sudah dibangun lengkap buat dua-duanya, tapi **dua-duanya gak akan jalan** sampai BE nambah endpoint yang didokumentasikan di sini. Pola sama kayak `plan/handoff-audio-playback-reminder.md` — FE duluan, BE nyusul, debug bareng begitu endpoint-nya live.

Catatan: fitur ketiga yang diminta bareng ini — **popup "lengkapi profil" setelah login** — **sudah jalan penuh sekarang**, gak butuh BE apapun (reuse `PATCH /auth/me` yang sudah ada). Gak dibahas di dokumen ini karena gak ada yang perlu dikerjakan BE.

---

## Fitur 1: Foto Profil

### Kondisi Saat Ini

Tombol kamera di halaman Profile (`frontend/app/(main)/profile/page.tsx`) sebelumnya cuma dekorasi, gak ada `onClick` sama sekali. `UserProfile` (`GET /auth/me`) juga belum punya field foto sama sekali.

### Scope BE

1. **Kolom baru** di `User`: `avatar_url` (nullable string).
2. **Endpoint upload:**
   ```
   POST /auth/me/avatar
   Content-Type: multipart/form-data
   Field: "file" (image/*)

   200 OK — balikin UserProfile lengkap (termasuk avatar_url yang baru)
   400 Bad Request — bukan file gambar / kegedean
   ```
3. **Endpoint hapus (opsional, buat "reset ke default"):**
   ```
   DELETE /auth/me/avatar
   200 OK — balikin UserProfile dengan avatar_url: null
   ```
4. **Penyimpanan:** disaranin reuse pola MinIO yang sudah ada di `services/storage.py` (bucket sama atau bucket baru khusus avatar, terserah).

### Keputusan penting: `avatar_url` harus BISA DIAKSES LANGSUNG dari browser (beda dari kasus audio!)

Ini kebalikan dari pendekatan yang dipakai di audio playback (`plan/handoff-audio-playback-reminder.md`) — di situ sengaja proxy lewat backend yang authenticated karena rekaman itu sensitif dan cuma dipakai di satu tempat. Foto profil **beda karakteristiknya**:

- **Sensitivitasnya jauh lebih rendah** — foto profil emang dimaksudkan buat dilihat orang lain di app (bukan data privat kayak rekaman rapat).
- **Dipakai berulang di banyak tempat** (halaman Profile, dan berpotensi navbar/daftar peserta ke depannya) — kalau tiap tempat harus fetch-as-blob pakai auth header kayak audio, jadi berat dan ribet buat direplikasi di banyak komponen.

Rekomendasi: `avatar_url` yang dibalikin API itu **URL yang langsung bisa dipasang ke `<img src>`** tanpa perlu header auth — baik itu:
- Object di bucket MinIO/R2 yang **public-read**, atau
- Presigned URL dengan masa berlaku panjang (misal 7 hari, di-refresh tiap kali `GET /auth/me` dipanggil).

FE sudah dibangun dengan asumsi ini — `frontend/app/(main)/profile/page.tsx` render `<img src={profile.avatar_url}>` langsung, **tanpa** fetch-as-blob kayak pola audio.

### Kontrak yang FE sudah asumsikan

- `lib/api.ts` — `uploadAvatar(file)` → `POST /auth/me/avatar` multipart, `deleteAvatar()` → `DELETE /auth/me/avatar`.
- `hooks/useProfile.ts` — `useUploadAvatar()`, `useDeleteAvatar()`, keduanya nge-update cache `["profile"]` dari response.
- FE **belum kasih batas ukuran/format resmi** dari BE — sekarang validasi cuma di FE (`image/*`, maks 5MB, angka sembarang buat jaga-jaga). Kalau BE punya batas beda, kasih tau supaya FE disamain.

### Cara Verifikasi

1. Buka `/profile`, klik ikon kamera → pilih gambar → foto muncul menggantikan ikon default, tanpa reload.
2. Refresh halaman → foto tetap muncul (bukti `avatar_url` beneran tersimpan & bisa diakses ulang).
3. Upload file bukan gambar (misal `.txt`) → dapat 400, FE nampilin toast error.

---

## Fitur 2: RSVP Konfirmasi Kehadiran

### Kondisi Saat Ini

`AttendanceStatus` (`pending | hadir | tidak_hadir`) yang ada sekarang itu status **presensi hari-H** (dicatat lewat check-in), bukan konfirmasi "akan hadir" sebelum rapat. Gak ada field yang bisa dipakai ulang buat RSVP — perlu field & endpoint baru, terpisah dari attendance.

### Scope BE

1. **Kolom baru** di `MeetingParticipant`: `rsvp_status` (enum: `pending | akan_hadir | tidak_hadir`, default `pending`). **Ikuti pola Alembic-enum yang didokumentasikan `CLAUDE.md`** (bikin type dulu `checkfirst=True`, jangan `sa.Enum()` langsung di `create_table`/`add_column`).
2. **Endpoint baru**, self-service oleh participant yang login (pakai `current_user`, cari `MeetingParticipant` miliknya di meeting itu — **bukan** dari `checkin_token` kayak self check-in):
   ```
   PATCH /meetings/{meeting_id}/rsvp
   Body: { "response": "akan_hadir" | "tidak_hadir" }

   200 OK — balikin MeetingDetail atau ParticipantResponse yang sudah keupdate
   403 Forbidden — current_user bukan participant meeting ini
   404 Not Found — meeting gak ditemukan
   ```
3. `ParticipantResponse` (schema yang sudah ada) perlu nambah field `rsvp_status` di response-nya — supaya FE bisa baca status RSVP peserta lain juga (organizer bisa liat siapa yang udah konfirmasi, kalau nanti mau dibikin agregatnya).

### Kontrak yang FE sudah asumsikan

- `lib/api.ts` — `submitRsvp(meetingId, response)`.
- `hooks/useMeeting.ts` — `useSubmitRsvp(meetingId)`, invalidate `["meeting", id]` on success.
- Card "Konfirmasi Kehadiran" di `frontend/app/(main)/meetings/[id]/page.tsx` — muncul buat participant (bukan organizer) **cuma kalau `meeting.status === "scheduled"`** (belum berlangsung). Baca `myParticipant.rsvp_status`, dan render 2 tombol ("Ya, akan hadir" / "Tidak bisa hadir") kalau masih `pending`.

### Yang sengaja BELUM dibangun di FE (di luar scope ini, catat aja)

- **View agregat buat organizer** ("5 dari 8 peserta konfirmasi hadir") — belum ada UI-nya. Kalau BE nambah `rsvp_status` ke `ParticipantResponse` (poin 3 di atas), FE bisa nambah ini belakangan tanpa endpoint baru lagi.
- **Reminder RSVP** (nagih peserta yang belum jawab) — di luar scope, bisa jadi fitur terpisah kalau dibutuhkan.

### Cara Verifikasi

1. Peserta buka meeting yang statusnya `scheduled` dan belum RSVP → card "Konfirmasi Kehadiran" muncul dengan 2 tombol.
2. Klik "Ya, akan hadir" → card berubah jadi state hijau "Kamu konfirmasi akan hadir", gak ada tombol lagi.
3. Refresh halaman → state RSVP tetap kebaca dari server (`myParticipant.rsvp_status`).
4. Meeting yang statusnya `completed`/`cancelled` → card ini gak muncul sama sekali (FE sudah gate dengan `meeting.status === "scheduled"`).
5. Organizer buka meeting yang sama → card ini gak muncul buat dia (RSVP cuma buat participant, bukan organizer).

---

## Catatan

Ketiga permintaan (foto profil, RSVP, popup lengkapi profil) diminta bareng dalam satu sesi kerja FE. Popup lengkapi profil sudah selesai total dan gak masuk dokumen ini karena nihil kerjaan BE. Foto profil & RSVP — FE sudah siap dan akan langsung berfungsi begitu endpoint di atas live, gak perlu perubahan FE tambahan.
