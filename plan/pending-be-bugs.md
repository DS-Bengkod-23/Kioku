# Bug yang Belum Terselesaikan — Perlu Fix di Backend

Dokumen ini berisi daftar bug yang sudah dianalisis dari sisi frontend, namun root cause-nya ada di backend. FE sudah siap menangani data jika BE mengembalikannya dengan benar.

---

## Bug 6 — Action Item Due Date Tidak Bisa Diedit

**Gejala:** Organizer tidak bisa mengubah ATAU menambahkan deadline pada action item yang sudah dibuat (baik hasil AI maupun manual). Deadline hanya bisa diisi saat membuat action item baru lewat form manual — begitu tersimpan (termasuk semua item hasil AI yang mayoritas `due_date`-nya kosong), field ini jadi read-only selamanya.

> **Catatan penting:** "Menambah deadline baru" (untuk item yang `due_date`-nya `null`, kasus paling umum untuk action item hasil AI) dan "mengedit deadline yang sudah ada" adalah **operasi backend yang identik** — keduanya sama-sama mengirim `due_date` lewat `PATCH /action-items/:id`, dan sama-sama diblokir oleh field yang sama di `ActionItemUpdateRequest`. Tidak perlu dianggap 2 pekerjaan terpisah; 1 perbaikan backend menyelesaikan keduanya sekaligus.

**Root cause (BE):**
`ActionItemUpdateRequest` (`schemas/action_item.py`) tidak punya field `due_date` — hanya `status` dan `assignee_participant_id`. Kalau FE kirim `due_date` di PATCH, Pydantic diam-diam membuang field yang tidak dideklarasikan, jadi tidak akan pernah tersimpan meskipun request-nya sukses (200 OK).

`update_action_item()` (`services/action_item.py`) juga tidak punya branch untuk field ini.

**FE siap implementasi** begitu BE support:
- Tinggal tambah `due_date` ke payload `updateActionItem()` di `lib/api.ts`
- Tambah UI inline date-edit di `ActionItemList.tsx` (saat ini due date pada item yang sudah ada hanya ditampilkan sebagai teks read-only; ada juga tombol "+ Deadline" untuk item yang belum punya due date, sekarang cuma menampilkan toast placeholder)
- Tambah handler `handleUpdateDueDate` di `meetings/[id]/page.tsx`, mirip pola `handleAssignTask`

**Yang perlu dilakukan BE:**
1. Tambah `due_date: Optional[date] = None` ke `ActionItemUpdateRequest`
2. Tambah branch di `update_action_item()`:
   ```python
   if "due_date" in update_data:
       if not is_organizer:
           raise HTTPException(status_code=403, detail="Hanya organizer yang bisa ubah deadline")
       action_item.due_date = update_data["due_date"]
   ```
3. **(Opsional, terkait urutan action item)** Tambah kolom `created_at` ke model `ActionItem` + migration. Saat ini tabel `ActionItem` tidak punya timestamp sama sekali dan `id`-nya UUID random (bukan sequential), jadi tidak ada cara stabil untuk urutkan berdasarkan waktu dibuat. FE sudah workaround dengan sort by due date di frontend, tapi kalau butuh urutan "terbaru dulu" di masa depan, ini prasyaratnya.

> **Catatan:** `source` field (`ai` | `manual`) sudah ada di model `ActionItem` tapi belum di-expose ke API response — kalau nanti dibutuhkan untuk membedakan tampilan item AI vs manual di FE, perlu ditambahkan juga ke `ActionItemResponse`.

---

## Bug 7 — Dashboard Rapat Belum Bisa Dicari Berdasarkan Tanggal

**Gejala:** Search box di dashboard rapat (`/meetings`) cuma bisa cari berdasarkan judul/isi rapat, tidak bisa filter berdasarkan tanggal jadwal rapat (`scheduled_at`).

**Root cause (BE):**
`search_meetings()` (`services/meeting.py`) melakukan `ILIKE` cuma di 3 kolom teks: `Meeting.title`, `Summary.tldr`, `ActionItem.task` — `Meeting.scheduled_at` sama sekali tidak ikut di-query. Ketik tanggal di search box sekarang tidak akan match apapun kecuali tanggal itu kebetulan muncul sebagai teks di judul/summary.

Endpoint `GET /meetings/search` (`routers/meetings.py`) cuma terima param `q`, `page`, `limit` — tidak ada param tanggal.

**Sudah ada pola yang bisa dicontoh:** Endpoint `GET /meetings` (list biasa, bukan search) sudah punya filter `status` sebagai query param terpisah (bukan dicampur ke text search):
```python
if status:
    query = query.filter(Meeting.status == status)
```
Filter tanggal bisa dibuat dengan pola yang sama, ditambahkan sebagai `.filter()` terpisah (AND, bukan bagian dari `or_()` text search).

**FE sudah siap UI-nya:** Tombol "Tanggal" sudah ada di dashboard (`meetings/page.tsx`), tapi sementara cuma menampilkan toast info karena belum ada yang bisa disambungkan ke backend.

**Yang perlu dilakukan BE:**
1. Tambah query param opsional di `routers/meetings.py`, misal `date_from: Optional[date] = None, date_to: Optional[date] = None`, untuk endpoint `GET /meetings` DAN `GET /meetings/search`
2. Tambah filter clause di `get_meetings()` dan `search_meetings()` (`services/meeting.py`):
   ```python
   if date_from:
       query = query.filter(Meeting.scheduled_at >= date_from)
   if date_to:
       query = query.filter(Meeting.scheduled_at < date_to + timedelta(days=1))
   ```
   Pastikan ini clause `AND` terpisah, bukan digabung ke dalam `or_(...)` yang sudah ada — kalau digabung ke `or_()` hasil justru akan melebar, bukan menyempit.

**Yang perlu dilakukan FE setelah BE siap:**
- `lib/api.ts`: tambah `date_from?`/`date_to?` ke `MeetingsParams` dan ke `searchMeetings()`
- `hooks/useMeetings.ts`: teruskan param baru ke query key & query function
- `meetings/page.tsx`: ganti `handleDateFilterAttempt` (toast placeholder) jadi date range picker yang beneran, sambungkan ke `useMeetings`/`useSearchMeetings`

---

## Bug 8 — PDF Notulen: Beberapa Masalah Teknis Layout

**Gejala:** User awalnya minta tampilan/susunan PDF notulen diperbaiki, tapi belum kasih detail spesifik yang diinginkan (belum ada referensi visual). Karena PDF ini 100% digenerate di backend (`services/pdf.py`, fungsi `generate_notulen_pdf()` pakai `fpdf`) — nol kode PDF di frontend — berikut masalah teknis objektif yang ditemukan dari membaca kode-nya.

> **Catatan penting:** Ini BUKAN daftar requirement redesign lengkap. Preferensi tampilan/susunan yang lebih spesifik (tata letak, urutan section, gaya visual) belum ditentukan — 4 poin di bawah murni masalah teknis yang bisa dilihat langsung dari kode. Kalau nanti ada requirement visual lebih detail, akan menyusul terpisah.

**Root cause (BE) — 4 masalah teknis di `services/pdf.py`:**

1. **Teks bisa overflow/tabrakan antar kolom** (baris 119, 194) — nama peserta (`col_name`) dan deskripsi tugas action item pakai `pdf.cell()` biasa, bukan `multi_cell()`. `cell()` di fpdf tidak wrap teks — kalau isinya lebih panjang dari lebar kolom, teks akan nembus keluar border dan bisa tumpang tindih dengan kolom di sebelahnya.
2. **Kolom "Tugas" dipotong paksa 55 karakter** (baris 194): `ai.task[:55] + "..."` — deskripsi action item yang panjang akan terlihat terpotong, bukan wrap ke baris berikutnya.
3. **Header tabel tidak berulang di halaman baru** — baik tabel PESERTA maupun ACTION ITEMS dirender sebagai baris `cell()` biasa tanpa penanganan page-break; kalau tabel meluber ke halaman berikutnya (peserta/action item banyak), baris data di halaman baru tidak akan punya label kolom (No/Nama/Status, dst).
4. **Tidak ada nomor halaman** — untuk notulen yang panjangnya lebih dari 1 halaman, tidak ada penanda halaman ke berapa dari berapa.

**Yang perlu dilakukan BE:**
- Ganti `cell()` jadi `multi_cell()` untuk kolom nama peserta & tugas action item supaya teks panjang wrap, bukan overflow
- Hapus truncation `[:55]` pada task, biarkan wrap alami
- Tambah logic cek sisa tinggi halaman sebelum render baris tabel; kalau mepet, panggil `add_page()` + cetak ulang header tabel
- Tambah `pdf.cell(0, 5, f"Halaman {pdf.page_no()}", align="R")` di footer tiap halaman

---

## Ringkasan (Aktif)

| # | Bug | File BE yang perlu diubah | Prioritas |
|---|---|---|---|
| 6 | Due date action item tidak bisa diedit | `schemas/action_item.py`, `services/action_item.py` | Medium |
| 7 | Search rapat berdasarkan tanggal | `routers/meetings.py`, `services/meeting.py` | Low |
| 8 | PDF notulen — overflow teks, tabel terpotong, tanpa nomor halaman | `services/pdf.py` | Low |

---

## Riwayat — Sudah Diperbaiki

Bug-bug ini sebelumnya tercatat di dokumen ini, tapi sudah dikonfirmasi FIXED di kode backend saat ini (dicek ulang 2026-07-05). Dibiarkan di sini sebagai riwayat, bukan tindakan yang masih perlu dilakukan.

### ~~Bug 1 — Peserta Baru Tidak Dapat Email saat Edit Rapat~~ ✅ Fixed
`MeetingUpdate` sekarang punya `participant_emails: Optional[List[str]]` (`schemas/meeting.py`), dan `update_meeting()` (`services/meeting.py`) memproses penambahan/penghapusan peserta serta mengirim email undangan ke peserta baru lewat `send_invitation_email()`.

### ~~Bug 2 — QR Code Tidak Muncul~~ ✅ Fixed
`ParticipantResponse` sekarang punya `checkin_token: Optional[str]`, diisi dari `data.invitation.token` di `extract_fields()`.

### ~~Bug 4 — Status "Tidak Hadir" Tidak Otomatis Saat Presensi Ditutup~~ ✅ Fixed
`complete_meeting()` (`services/meeting.py`) sekarang otomatis mengubah semua status peserta `pending` → `tidak_hadir` saat rapat di-complete (`attendance_locked = True`).

### ~~Bug 5 — Notulen Tidak Muncul di Portal Check-In (Magic Link)~~ ✅ Fixed
`get_checkin_info()` (`services/checkin.py`) sekarang mengembalikan `summary`, `action_items` (difilter per assignee), `processing_status`, dan status expired berdasarkan `meeting_end`/`attendance_locked` — sesuai kebutuhan `CheckinPageResponse`.
