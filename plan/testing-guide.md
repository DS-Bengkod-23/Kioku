# Panduan Testing — Fitur Terbaru Kioku

**Tanggal:** 2026-07-22
**Branch:** `backend` (sudah gabungan kode BE terbaru + FE dari Helena)
**Buat siapa:** siapa aja di tim yang mau bantu tes sebelum dibuka PR ke `main`
**Sifat dokumen:** panduan tes manual, bukan kontrak API — kontrak detail per fitur ada di `plan/handoff-*.md`

---

## 0. Setup sekali di awal

```bash
git checkout backend
git pull origin backend

docker compose build backend-api   # ada dependency baru (Pillow, buat validasi foto profil)
docker compose build frontend
make up
make migrate
```

Kalau `make migrate` gak dijalanin, nanti login/pakai app bisa error `column ... does not exist`.

### Bikin akun admin (kalau di database kamu belum ada sama sekali)

Cek dulu — kalau udah pernah ada admin/superadmin di databasemu, skip langkah ini.

```bash
docker compose exec backend-api python scripts/seed_admin.py --email admin@kioku.local --password admin12345
```

Ini bikin **akun baru** dengan role `superadmin`. Login pakai email/password itu buat tes bagian Admin Panel di bawah. Kalau mau akun harianmu sendiri juga jadi admin, login sebagai `admin@kioku.local` dulu, lalu promote akunmu lewat `/admin` → Users.

---

## 1. Tools yang dipakai

| Tool | URL | Buat apa |
|---|---|---|
| App (frontend) | http://localhost:3000 | Tempat tes semua fitur |
| Swagger (API docs) | http://localhost:8000/docs | Coba endpoint langsung tanpa lewat UI, kalau perlu debug |
| Mailhog | http://localhost:8025 | Lihat email yang "terkirim" (undangan, reset password, reminder) — gak beneran keluar ke inbox asli |
| Adminer | http://localhost:8080 | Lihat isi database langsung (server: `postgres`, user/db: `meetmate`) |

## 2. Akun yang dibutuhkan

Minimal siapin:
- **1 akun organizer** — buat bikin meeting.
- **1 akun peserta lain** — buat tes RSVP & presensi dari sisi peserta (bukan organizer).
- **1 akun admin/superadmin** — dari langkah seed di atas.

Kalau mau pakai akun lama yang udah ada di databasemu (`audi@gmail.com`, `helena@gmail.com`, `azmi@gmail.com`, `kioku@gmail.com`), pastikan kamu tahu passwordnya — kalau enggak, register aja akun baru dari halaman `/register`.

---

## 3. Checklist Fitur

### 🆕 A. Foto Profil

1. Login → buka halaman **Profile**.
2. Klik ikon kamera → pilih file gambar (jpg/png/webp) → foto harus muncul **tanpa reload halaman**.
3. Refresh halaman → foto harus **tetap ada** (bukan balik ke ikon default).
4. Coba upload file bukan gambar (misal `.txt` atau `.pdf`) → harus muncul **error, bukan foto ke-upload**.
5. Coba upload file gambar > 5MB → harus ditolak juga (error ukuran file).
6. Klik hapus foto (kalau ada tombolnya) → foto balik ke ikon default, dan tetap default setelah refresh.

### 🆕 B. RSVP Konfirmasi Kehadiran

1. Login sebagai **organizer**, bikin meeting baru dengan status `scheduled` (belum lewat waktunya), masukin akun peserta lain sebagai peserta.
2. Login sebagai **peserta** itu, buka meeting yang sama → harus muncul card **"Konfirmasi Kehadiran"** dengan 2 tombol.
3. Klik **"Ya, akan hadir"** → card berubah jadi state hijau, tombol hilang.
4. Refresh halaman → status RSVP harus **tetap kebaca** (gak balik ke pending).
5. Login lagi sebagai **organizer** di meeting yang sama → card RSVP **gak boleh muncul** buat organizer.
6. (Opsional) Login sebagai akun yang **bukan peserta meeting itu** dan coba akses endpoint RSVP-nya lewat Swagger → harus dapat error 403.

### 🆕 C. Admin Panel

1. Login sebagai admin/superadmin → buka `/admin`.
2. **Users**: lihat daftar user, coba suspend salah satu user (bukan diri sendiri) → user itu harus gak bisa login lagi. Unsuspend → bisa login lagi.
3. **Users**: coba promote seorang user jadi admin, lalu demote balik.
4. **Meetings**: coba soft-delete satu meeting → login sebagai peserta meeting itu, buka meeting-nya → harus muncul notice generik "meeting ini telah dihapus", bukan error/404.
5. **Audit Logs**: setelah aksi-aksi di atas, cek halaman Audit Logs → semua aksi admin (suspend, promote, delete) harus tercatat dengan nama admin yang ngelakuin.
6. **Reset password paksa**: dari halaman Users, minta reset password buat satu user → cek Mailhog (http://localhost:8025), harus ada email masuk dengan link reset → buka link-nya, set password baru → coba login pakai password baru itu.

> **Catatan:** tombol hapus recording di admin panel kemungkinan belum ada/belum jalan — itu gap yang sudah diketahui (backend belum expose ID recording-nya ke Helena), **bukan bug baru**, gak perlu dilaporkan.

### ♻️ D. Smoke test fitur yang udah lama jadi (pastiin gak keregresi)

Gak perlu detail banget, cukup pastiin gak error:

- **Login/Register manual** (email+password).
- **Login Google SSO** — kalau `GOOGLE_SSO_ENABLED=true` di `.env`.
- **Connect Google Calendar** dari halaman Kalender, cek event muncul di Google Calendar asli.
- **Upload rekaman** meeting → status berubah `queued` → `transcribing` → ... → `completed`, notulen & action item muncul otomatis tanpa refresh manual.
- **Playback audio** rekaman yang sudah selesai diproses.
- **Presensi** (check-in) via link email undangan (cek Mailhog) → status di meeting berubah jadi hadir.
- **Popup lengkapi profil** muncul sekali pas pertama login kalau profil masih kosong.

---

## 4. Cara Lapor Hasil

Kalau ketemu yang aneh, kasih tau:
1. Nama fitur & langkah persis yang dilakuin.
2. Yang diharapkan vs yang kejadian.
3. Screenshot kalau ada tampilan yang salah, atau copy pesan error kalau ada (dari console browser / terminal `docker compose logs backend-api`).
