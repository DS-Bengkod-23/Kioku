# Handoff untuk Backend — Yang Harus Dikerjakan

**Tanggal:** 2026-07-08
**Branch:** `frontend`

FE sudah menambahkan beberapa fitur yang sebagian fungsinya nunggu backend. Berikut daftar tugas yang perlu BE kerjakan, diurutkan prioritas.

---

## Sudah Selesai (dikonfirmasi 2026-07-08, tidak perlu dikerjakan lagi)

✅ **`POST /meetings/{id}/action-items`** — sudah diverifikasi ADA dan lengkap di `main`/`frontend` HEAD (commit `37c9e41`): schema `ActionItemCreateRequest` (`app/schemas/action_item.py`), service `create_action_item()` (`app/services/action_item.py`), route terdaftar di `app/routers/meetings.py` dan sudah di-`include_router` di `main.py`. Field `assignee_participant_id` di `ActionItemUpdateRequest` juga sudah ada — assign action item via PATCH sudah berfungsi.

Kalau FE masih dapat 404 saat memanggil endpoint ini, itu **bukan** karena BE belum implement — kemungkinan besar backend container lokal FE belum jalan dengan kode terbaru (misalnya karena `make build` gagal — lihat catatan pip error di bawah). Cek dulu apakah container `backend-api` sukses di-build & running sebelum menyimpulkan ada yang kurang di BE.

*(Dokumen `plan/done-action-items-improvements.md` dan `plan/pending-be-bugs.md` masih menyebut endpoint ini "belum ada" — itu sudah basi, endpoint-nya sudah diimplementasikan Audi setelah dokumen itu ditulis.)*

---

## Yang Harus Dikerjakan BE

### 1. [Medium] Tambah `due_date` ke `ActionItemUpdateRequest`
FE sudah punya tombol "+ Deadline" untuk action item yang belum ada due date-nya, dan due date pada item existing seharusnya bisa diedit — saat ini keduanya diblokir karena field `due_date` tidak ada di schema PATCH, jadi kalau FE kirim, Pydantic diam-diam membuangnya (200 OK tapi tidak tersimpan).

- **Yang perlu diubah:**
  - `app/schemas/action_item.py` — tambah `due_date: Optional[date] = None` ke `ActionItemUpdateRequest`
  - `app/services/action_item.py` — tambah branch di `update_action_item()` untuk field ini (hanya organizer yang boleh ubah)
- **Detail root cause & contoh kode:** `plan/pending-be-bugs.md` (Bug 6)

### 2. [Low] Filter tanggal di `GET /meetings` dan `GET /meetings/search`
FE sudah punya tombol "Tanggal" di dashboard rapat (masih placeholder/toast) yang nunggu ini. Filter ini juga akan dibutuhkan oleh fitur Kalender Rapat yang baru — saat ini Kalender narik semua meeting lewat `limit=100`, kalau jumlah rapat tim makin banyak akan mentok limit.

- **Yang perlu ditambah:** query param opsional `date_from`/`date_to` di kedua endpoint (`routers/meetings.py`), filter `.filter(Meeting.scheduled_at >= date_from)` dkk di `services/meeting.py` — pola sama seperti filter `status` yang sudah ada
- **Detail lengkap:** `plan/pending-be-bugs.md` (Bug 7)

### 3. [Opsional] Review `backend/.env.example`
FE menambahkan file ini sebagai referensi variabel environment (`DATABASE_URL`, `REDIS_URL`, `MINIO_*`, `SECRET_KEY`, `SMTP_*`, `FRONTEND_URL`). Tolong dicek apakah isinya akurat/lengkap dibanding `.env` asli yang dipakai backend — dibuat dari sisi FE jadi bukan sumber kebenaran.

### 4. [Info — sudah ada di backlog, bukan blocker] Perbaikan layout PDF notulen
4 masalah teknis di `services/pdf.py` (teks overflow, kolom task terpotong 55 karakter, header tabel tidak repeat di halaman baru, tidak ada nomor halaman). Prioritas Low, dicantumkan di sini sebagai reminder — detail lengkap di `plan/pending-be-bugs.md` (Bug 8).

### 5. [FYI — bukan tugas kode] `backend/requirements.txt` build gagal (pip ResolutionImpossible)
`make build` gagal di step `pip install -r requirements.txt` karena `pydantic` tidak dipin eksplisit — pip harus backtracking coba puluhan versi (2.7.0–2.13.4) dan di jaringan lambat ini bisa gagal dengan error `ResolutionImpossible` yang membingungkan (padahal versinya sebenarnya kompatibel dengan `fastapi==0.115.12` & `pydantic-settings==2.9.1`). Fix: tambah pin eksplisit, misal `pydantic==2.10.6`, ke `backend/requirements.txt`.

---

## Perubahan yang Sudah Dikerjakan FE

Ini bukan hal yang perlu BE tindak lanjuti — cuma supaya BE tahu apa saja yang berubah di sisi FE pada branch `frontend` ini.

### Fitur Baru

| Fitur | File | Keterangan |
|---|---|---|
| Kalender Rapat (`/calendar`) | `frontend/app/(main)/calendar/page.tsx` (baru) | Tampilan bulanan, klik tanggal untuk lihat daftar rapat di hari itu. Ambil data lewat `useMeetings({ limit: 100 })` lalu dikelompokkan per tanggal di client. |
| Nav link "Kalender" | `frontend/app/(main)/layout.tsx` | Menu baru di header dashboard, di antara "Rapat" dan "Tugas Saya". |
| Hero + ringkasan statistik Dashboard | `frontend/app/(main)/meetings/page.tsx` | Panel atas digabung: sapaan, tombol "Buat Rapat", dan 4 angka (Total/Dijadwalkan/Selesai/Dibatalkan). |
| Hero + ringkasan statistik Tugas Saya | `frontend/app/(main)/action-items/page.tsx` | Layout serupa: total tugas, aktif, selesai. |
| Sort action items by due date | `frontend/app/(main)/meetings/[id]/page.tsx` | Item tanpa due date otomatis ditaruh di akhir daftar. |
| Tombol "Tanggal" (placeholder) | `frontend/app/(main)/meetings/page.tsx` | UI sudah ada, masih toast info — nunggu item #2 di "Yang Harus Dikerjakan BE". |
| Tombol "+ Deadline" (placeholder) | `frontend/components/notulen/ActionItemList.tsx` | Muncul untuk action item tanpa due date — masih toast info, nunggu item #1 di "Yang Harus Dikerjakan BE". |

### Bug Fix (FE-only)

| Bug | File | Fix |
|---|---|---|
| PDF notulen gagal di-download di Firefox | `frontend/lib/api.ts` | Element `<a>` sekarang di-`appendChild` ke DOM sebelum `.click()`, lalu di-`removeChild` setelahnya. |
| Assign action item gagal tanpa feedback | `frontend/app/(main)/meetings/[id]/page.tsx` | `handleAssignTask` sekarang `await` dan tampilkan toast error kalau gagal. |
| Form edit rapat salah include organizer di daftar peserta existing | `frontend/app/(main)/meetings/[id]/edit/page.tsx` | `existingEmails` sekarang filter keluar participant dengan `role === "organizer"`. |
| Update meeting lambat ke-refresh di UI | `frontend/hooks/useMeeting.ts` | `useUpdateMeeting` pakai `queryClient.setQueryData` dengan response terbaru, bukan cuma `invalidateQueries`. |

### Rebrand: MeetMate → Kioku

Ganti nama aplikasi di semua teks yang tampil ke user: title/meta halaman, logo header (dashboard, auth pages, check-in portal, landing page), footer copyright, dan copy FAQ/testimonial di landing page. Tidak ada perubahan skema data, endpoint, atau identifier internal. Sekalian, warna aksen brand diseragamkan dari campuran `blue-600`/`blue-700` menjadi `indigo-600` di seluruh komponen — murni visual, tidak ada perubahan behavior.

---

Peta lengkap semua halaman/fungsi FE ada di `plan/frontend-guide.md`. Riwayat sesi sebelumnya (auth redirect, logout, polling restart) ada di `plan/session-log.md`.
