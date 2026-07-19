# Desain Role Admin & Superadmin

**Status:** Keputusan desain sudah final lewat diskusi (18 Juli 2026). **Belum diimplementasikan** — dokumen ini cuma mencatat keputusannya, implementasi menyusul di PR terpisah.

## Kenapa

Saat ini `User` (`backend/app/models/user.py`) belum punya role sama sekali secara global — yang ada cuma role per-meeting lewat `MeetingParticipant` (organizer vs peserta), sesuai catatan "Auth Model" di `CLAUDE.md`. Dibutuhkan role admin karena dua kebutuhan konkret:

1. **User management** — suspend akun, reset password, dll.
2. **Audit & compliance lintas meeting** — admin perlu bisa mengecek data di luar meeting yang dia ikuti sendiri.

## Keputusan

### Level role

Dua tier: **`admin`** dan **`superadmin`**. Bukan role flat tunggal — pemisahan ini supaya gak semua admin bisa bikin admin baru sesuka hati.

### User management

| Kemampuan | Siapa yang punya |
|---|---|
| Bikin user baru manual | **Tidak ada** — tetap lewat form registrasi biasa |
| Edit profil user lain | **Tidak ada** |
| Suspend / unsuspend akun (soft, bukan hard delete) | Admin & superadmin |
| Hard delete user | **Belum dibangun** — sengaja ditunda |
| Reset password user (local auth) | **Superadmin only** |
| Promote / demote admin | **Superadmin only** |
| Cabut koneksi Google SSO/Calendar user lain | **Tidak ada** — di-drop, gak ada use case jelas (user sudah bisa self-service via `DELETE /auth/google/calendar`) |

### Akses isi meeting (audit & compliance)

- **Default: metadata-only** untuk semua meeting di sistem — judul, waktu, organizer, daftar peserta, status kehadiran, status action item. Admin **tidak** otomatis bisa baca transcript/notulen/summary.
- Untuk baca isi (transcript/notulen/summary) meeting tertentu, admin mengisi alasan singkat lalu **langsung dapat akses saat itu juga** — **tidak ada approval gate** (dijuluki "Model 1" selama diskusi). Alasan yang diisi wajib tercatat di audit log.
  - Alternatif yang sempat dibahas dan **ditunda** (bukan dibatalkan): akses baru diberikan setelah di-approve superadmin ("Model 2"). Bisa direvisit kalau Model 1 terbukti kurang ketat di praktiknya.
- **Rekaman audio mentah (dengar/download) permanen off-limits buat admin**, walaupun sedang dalam mode akses isi meeting. Akses isi cuma membuka teks transcript/notulen, gak pernah file audio asli. Alasan: suara itu data biometrik, teks sudah cukup buat keperluan compliance.

### Data yang tetap off-limits buat admin (walau role admin/superadmin)

- Password hash — gak pernah diexpose lewat API manapun (standar, bukan hal baru).
- Token OAuth Google (`GoogleCalendarCredential.access_token` / `refresh_token`, terenkripsi Fernet) — admin cuma boleh lihat status koneksi (connected/disconnected), gak pernah token ter-decrypt.
- File audio rekaman asli (lihat poin di atas).

### Audit log

Wajib ada, mencatat siapa-ngapain-kapan-kenapa untuk semua aksi sensitif: request akses isi meeting, suspend/unsuspend, promote/demote, delete meeting/recording.

Fitur export log ke file untuk laporan compliance **tidak dibutuhkan** saat ini.

### Delete meeting/recording

Admin bisa hapus meeting/recording tertentu; aksi ini masuk audit log yang sama.

### Notifikasi ke peserta

**Tidak ada notifikasi sama sekali** ke organizer/peserta saat admin mengakses isi meeting mereka — sengaja, supaya gak "membocorkan" ke subjek investigasi bahwa meeting-nya sedang diperiksa.

### Bootstrap admin pertama

Admin/superadmin pertama dibuat lewat **seed script**, bukan lewat UI aplikasi (karena belum ada admin yang bisa mempromosikan siapa pun di awal).

### UI

Route terpisah **`/admin`** di frontend Next.js (mirip pola grup `(auth)` yang sudah ada) — bukan menempel di halaman dashboard biasa. Nav item ini cuma muncul kalau role user adalah admin/superadmin.

## Area yang akan tersentuh saat implementasi (belum dikerjakan)

- Migration + kolom role baru di `User` (dan kemungkinan tabel audit log baru).
- Endpoint admin di backend (user management, meeting audit view, request akses isi meeting, audit log).
- Dependency auth baru (semacam `get_current_admin_user` / `get_current_superadmin_user`).
- Seed script untuk admin pertama.
- Route group `/admin` + guard role di frontend.
