# Ringkasan Kerjaan FE — Kioku

**Tanggal:** 2026-07-20
**Branch:** `frontend`
**Sifat dokumen:** Log/ringkasan progres, bukan dokumen perencanaan atau kontrak API — kontrak detail ada di masing-masing `plan/handoff-*.md`.

---

## Sudah 100% berfungsi (gak nunggu BE apapun)

| Fitur | Keterangan |
|---|---|
| Breakdown status processing per-stage | Meeting detail page nampilin label spesifik ("Sedang transkripsi audio...", dst), bukan teks generik lagi |
| Auto-refresh notulen setelah processing selesai | Fix bug: summary/transkrip dulu butuh refresh manual, sekarang otomatis muncul |
| Presensi: rename + gaya + auto-lock | "Check In" → "Presensi", card tertutup jadi merah, auto-lock kalau lewat deadline (dihitung ulang di FE tiap menit) |
| Banner ajakan connect Google Calendar | Muncul di halaman Kalender buat yang belum connect |
| Reminder action item (notifikasi browser) | Lonceng di navbar, notifikasi native browser buat task mendekati deadline |
| Popup lengkapi profil | Muncul sekali setelah profil kedetek kosong |
| Fix redirect setelah login | `?redirect=` dari middleware sekarang beneran dipakai (dulu selalu ke `/meetings`) |

## FE sudah siap, nunggu integrasi BE

| Fitur | Dokumen kontrak |
|---|---|
| Login & Calendar Sync via Google | `plan/handoff-google-integration.md` |
| Audio playback rekaman | `plan/handoff-audio-playback-reminder.md` |
| Reminder action item versi email (H-1) | `plan/handoff-audio-playback-reminder.md` — **sudah dikonfirmasi BE-nya live** (commit `67a3f0a` Audi) |
| Foto profil (upload avatar) | `plan/handoff-avatar-rsvp.md` |
| RSVP konfirmasi kehadiran sebelum rapat | `plan/handoff-avatar-rsvp.md` |
| Admin & Superadmin (`/admin/*`, `/reset-password/[token]`) | `plan/admin-role-frontend-handoff.md` — **status BE belum terkonfirmasi ada di GitHub**, cek dulu sebelum tes |

## Dokumen referensi yang sudah dibuat

- `plan/handoff-google-integration.md`
- `plan/handoff-audio-playback-reminder.md`
- `plan/handoff-avatar-rsvp.md`
- `plan/admin-role-implementation-roadmap.md` — urutan fase implementasi yang disarankan
- `plan/admin-role-design.md` / `docs/admin-role-design.md` — **catatan: dua file ini isinya identik (duplikat), belum dirapikan jadi satu**

## Yang masih perlu tindak lanjut

1. Konfirmasi ke Audi soal status push kode admin role.
2. `DELETE /recordings/{recording_id}` (admin) belum ada tombolnya di UI — `MeetingAdminResponse` gak punya field recording ID, perlu ditanyakan ke Audi.
3. Rapikan duplikat `docs/admin-role-design.md` vs `plan/admin-role-design.md`.
4. PR ke `main` baru dibuka setelah semua fitur di atas bisa dites ujung-ke-ujung.
