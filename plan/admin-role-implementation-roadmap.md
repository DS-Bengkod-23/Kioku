# Roadmap Implementasi — Admin & Superadmin

**Status:** Belum dikerjakan. Urutan di bawah disusun berdasarkan dependensi teknis (bagian belakang gak bisa dites tanpa bagian depan selesai duluan), bukan sekadar daftar sembarang. Rujukan keputusan desain: `docs/admin-role-design.md` / `plan/admin-role-design.md` (dua-duanya isinya sama — belum diberesin mana yang jadi satu-satunya sumber).

---

## Fase 0 — Fondasi (BE, wajib duluan, semua fase lain bergantung ke ini)

Gak ada satupun fase di bawah yang bisa mulai/dites tanpa ini kelar.

1. **Migration: kolom `role` di `User`** — enum `user | admin | superadmin`, default `user`. Ikuti pola Alembic-enum yang sudah didokumentasikan di `CLAUDE.md` (bikin type dulu dengan `checkfirst=True`, baru pakai `create_type=False` di kolomnya — biar gak kena `DuplicateObject` kayak kasus sebelumnya).
2. **Migration: tabel `AuditLog`** — minimal butuh: `actor_user_id`, `action` (enum/string: `suspend`, `unsuspend`, `promote`, `demote`, `access_meeting_content`, `delete_meeting`, `delete_recording`, dst), `target_type` + `target_id` (meeting/user yang kena aksi), `reason` (nullable — cuma diisi buat `access_meeting_content`), `created_at`.
3. **Auth dependency baru**: `get_current_admin_user` (admin atau superadmin lolos) dan `get_current_superadmin_user` (superadmin doang) — dibangun di atas `get_current_user` yang sudah ada, tinggal tambah pengecekan `user.role`.
4. **Seed script** admin/superadmin pertama — dijalankan manual di server, bukan lewat API/UI (karena di titik ini belum ada admin yang bisa promosikan siapa pun).

**Keluaran fase ini:** ada cara nge-tes "siapa admin/superadmin" dan nyatet audit log — tapi belum ada fitur admin apapun yang keliatan/kepake.

---

## Fase 1 — User Management (BE lalu FE)

### BE
1. `GET /admin/users` — list semua user (buat FE nampilin tabel).
2. `PATCH /admin/users/{id}/suspend` dan `.../unsuspend` — admin & superadmin, tulis ke audit log.
3. `PATCH /admin/users/{id}/reset-password` — **superadmin only**, tulis audit log.
4. `PATCH /admin/users/{id}/role` (promote/demote) — **superadmin only**, tulis audit log. Perlu validasi: superadmin gak bisa demote dirinya sendiri jadi user biasa kalau dia satu-satunya superadmin (biar sistem gak "terkunci" tanpa superadmin sama sekali — ini belum dibahas di dokumen desain, perlu diputuskan pas ngerjain).

### FE
1. Route group `/admin` baru (mirip pola `(auth)`) + layout dengan guard: render `null`/redirect kalau `role` user bukan admin/superadmin.
2. Nav item "Admin" di `app/(main)/layout.tsx` — cuma muncul buat role admin/superadmin.
3. Halaman `/admin/users` — tabel user + tombol suspend/unsuspend (semua admin), tombol reset password & ubah role (cuma keliatan/aktif kalau role login-nya superadmin).

**Kenapa fase ini duluan, bukan Fase 2:** lebih sederhana (CRUD biasa, gak ada workflow "Model 1" yang belum pernah dibangun polanya di app ini), jadi bagus buat validasi fondasi (role check, audit log) sebelum masuk ke bagian yang lebih rumit.

---

## Fase 2 — Audit & Akses Isi Meeting ("Model 1")

Ini bagian paling baru/berisiko — belum ada pola serupa di app ini sebelumnya (semua endpoint meeting yang ada sekarang selalu di-scope ke `organizer_id`/participant, belum pernah ada "lihat lintas semua meeting").

### BE
1. `GET /admin/meetings` — list **semua** meeting di sistem (bukan cuma yang admin ikut), metadata-only: judul, waktu, organizer, peserta, status kehadiran, status action item. **Tidak** include transcript/summary di response ini.
2. `POST /admin/meetings/{id}/access-content` — body `{ "reason": "..." }`, langsung balikin transcript/summary/notulen (bukan audio), tulis ke audit log (termasuk `reason`-nya).
3. `DELETE /admin/meetings/{id}` dan `DELETE /admin/meetings/{id}/recording` — tulis audit log.
4. Pastikan endpoint di atas **secara eksplisit tidak pernah** menyertakan `recording.file_url`/audio di response manapun — ini batasan permanen dari desain, bukan detail implementasi biasa, jadi perlu ditest secara sengaja (bukan cuma asumsi "gak dipanggil berarti aman").

### FE
1. Halaman `/admin/meetings` — tabel/list semua meeting (metadata-only).
2. Detail view per meeting: tampilan metadata dulu, tombol "Minta akses isi" → modal isi alasan → begitu submit langsung tampil transcript/summary di halaman yang sama (gak ada state "menunggu approval" karena Model 1 gak ada approval gate).
3. Tombol hapus meeting/recording (dengan konfirmasi).

---

## Fase 3 — Audit Log Viewer

### Satu hal yang perlu diputuskan dulu sebelum ngerjain ini
Dokumen desain **gak nyebut siapa yang boleh lihat audit log itu sendiri** — apakah admin cuma bisa lihat log aksi dia sendiri, atau semua admin bisa lihat log semua orang, atau ini superadmin-only? Ini perlu dijawab dulu (sama seperti kasus "gimana kalau superadmin terakhir demote diri sendiri" di Fase 1) sebelum mulai bikin endpoint & UI-nya.

### BE
- `GET /admin/audit-log` — dengan filter dasar (by actor, by action type, by tanggal). Visibility-nya nunggu keputusan di atas.

### FE
- Halaman `/admin/audit-log` — tabel log, filter simpel.

---

## Ringkasan urutan

```
Fase 0 (BE, fondasi)
   ↓
Fase 1 (BE → FE): User management
   ↓
Fase 2 (BE → FE): Audit & akses isi meeting — bagian paling berisiko/baru
   ↓
Fase 3 (BE → FE): Audit log viewer — nunggu keputusan visibility dulu
```

Saran: tiap fase jadi PR terpisah (bukan satu PR raksasa), biar direview lebih gampang dan Fase 0 bisa langsung dites fondasinya sebelum lanjut ke fase yang lebih kompleks.

## Keputusan kecil yang belum terjawab di dokumen desain (perlu disepakati pas/​sebelum implementasi)

1. Superadmin terakhir gak boleh demote diri sendiri (atau perlu selalu ada minimal 1 superadmin)?
2. Siapa yang boleh baca audit log — semua admin, atau superadmin-only?
