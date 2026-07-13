# Frontend Guide — MeetMate

Dokumen ini menjelaskan semua halaman, fungsi, dan alur pengguna di frontend MeetMate. Ditulis untuk anggota tim frontend agar bisa langsung paham tanpa harus baca kode dari nol.

---

## Stack & Struktur

- **Framework:** Next.js 14 App Router
- **State server:** React Query (`@tanstack/react-query`)
- **HTTP client:** axios (`lib/api.ts`)
- **UI components:** shadcn/ui + Tailwind CSS
- **Notifikasi:** sonner (toast)

```
frontend/
├── app/
│   ├── (auth)/          → halaman yang TIDAK butuh login
│   │   ├── login/
│   │   ├── register/
│   │   └── forgot-password/
│   ├── (main)/          → halaman yang BUTUH login (ada navbar)
│   │   ├── meetings/
│   │   │   ├── page.tsx         → Dashboard daftar rapat
│   │   │   ├── new/page.tsx     → Form buat rapat baru
│   │   │   └── [id]/
│   │   │       ├── page.tsx     → Detail rapat (utama)
│   │   │       └── edit/page.tsx → Form edit rapat
│   │   ├── action-items/page.tsx → Daftar tugas milik user
│   │   └── profile/page.tsx     → Profil & pengaturan akun
│   ├── check-in/[token]/page.tsx → Portal check-in (PUBLIK, tidak butuh login)
│   └── page.tsx                 → Landing page (publik)
├── components/
│   ├── meetings/        → MeetingCard, AttendanceTable, MeetingForm
│   ├── recording/       → UploadZone, ProcessingStatus
│   ├── notulen/         → SummaryCard, TranscriptView, ActionItemList
│   └── ui/              → shadcn components (jangan edit manual)
├── hooks/               → React Query wrappers
├── lib/
│   ├── api.ts           → semua fungsi HTTP ke backend
│   └── utils.ts         → helper: cn(), isDateOverdue(), extractApiError()
└── types/index.ts       → TypeScript types dari API
```

---

## Halaman & Fungsinya

### 1. Landing Page (`/`)
**File:** `app/page.tsx`

Halaman publik pertama yang dilihat orang. Tidak butuh login. Berisi:
- Hero section dengan animasi
- Fitur-fitur produk
- CTA (Call To Action) ke halaman register/login

---

### 2. Halaman Login (`/login`)
**File:** `app/(auth)/login/page.tsx`

**Yang terjadi saat login:**
1. User isi email + password → klik "Masuk Sekarang"
2. Frontend kirim `POST /auth/login`
3. Backend return `access_token` (JWT)
4. Token disimpan di `localStorage` (`access_token`) DAN di cookie (supaya middleware bisa baca)
5. Data profil user dibuat dari input form, disimpan ke `localStorage` (`user_profile`) dengan format:
   ```json
   { "name": "...", "email": "...", "role": "Team Member", ... }
   ```
6. Redirect ke `/meetings`

**Catatan penting:** `user_profile.email` dipakai di halaman detail rapat untuk menentukan apakah user adalah organizer. Kalau `user_profile` hilang dari localStorage, fitur organizer (assign action item, upload rekaman, edit rapat) tidak akan muncul.

---

### 3. Halaman Register (`/register`)
**File:** `app/(auth)/register/page.tsx`

Form pendaftaran akun baru. Kirim `POST /auth/register` lalu redirect ke `/login`.

---

### 4. Dashboard Rapat (`/meetings`)
**File:** `app/(main)/meetings/page.tsx`

**Fungsi utama:**
- Tampilkan semua rapat yang user ikut (sebagai organizer atau peserta)
- **Search:** debounce 300ms, pakai endpoint `/meetings/search?q=...`
- **Filter status:** Semua / Dijadwalkan / Selesai / Dibatalkan
- **Pagination:** 9 item per halaman
- Tombol **"Buat Rapat"** → ke `/meetings/new`

**Data yang ditampilkan per card:**
- Judul, status, tanggal, lokasi
- Jumlah peserta & yang hadir
- Badge jika sudah ada transkrip AI

---

### 5. Buat Rapat Baru (`/meetings/new`)
**File:** `app/(main)/meetings/new/page.tsx`  
**Component:** `components/meetings/MeetingForm.tsx`

**Field form:**
- Judul rapat (wajib)
- Lokasi / tautan
- Tanggal & waktu (wajib)
- Durasi (jam + menit)
- Deskripsi singkat
- Poin-poin agenda
- Daftar peserta (tambah via email, bisa tekan Enter atau klik +)

**Submit:** `POST /meetings` → sukses → redirect ke halaman detail rapat yang baru dibuat.

**Validasi lokal:**
- Email peserta harus mengandung `@`
- Tidak boleh tambah email yang sama dua kali
- Durasi tidak boleh 0 menit

**Setelah rapat dibuat:** Backend otomatis kirim email undangan ke semua peserta (via Mailhog di dev, atau Gmail di demo).

---

### 6. Detail Rapat (`/meetings/[id]`)
**File:** `app/(main)/meetings/[id]/page.tsx`

Ini halaman paling kompleks. Layout 2 kolom:

#### Kolom Kiri
- **Upload Rekaman** — hanya muncul untuk organizer. Drag-and-drop atau klik file (mp3/mp4/wav/m4a, max 200MB). Setelah upload, mulai polling status pemrosesan setiap 3 detik.
- **Informasi Rapat** — organizer, jadwal, lokasi, deskripsi, agenda.
- **Kehadiran** — tabel nama + status. Organizer bisa klik toggle Hadir / Tidak Hadir per peserta.

#### Kolom Kanan
- **Tab Ringkasan AI / Transkrip Audio** — muncul setelah rekaman selesai diproses
  - Ringkasan: executive summary, keputusan, topik
  - Transkrip: tiap segmen dengan timestamp dan nama pembicara
- **Tombol PDF** — muncul di sebelah tab, hanya aktif jika `processingStatus === "completed"`. Klik → download file `notulen-[judul].pdf`
- **Action Items** — daftar tugas hasil AI. Organizer bisa:
  - Klik item → toggle status (open/done)
  - Dropdown assign → ubah siapa yang bertanggung jawab
  - Tombol "Tambah action item manual" → form inline

#### Deteksi Organizer
```ts
const currentUserEmail = JSON.parse(localStorage.getItem("user_profile") || "{}").email;
const isOrganizer = meeting?.organizer?.email === currentUserEmail;
```
Kalau `isOrganizer === true`, tampilkan: tombol Edit Rapat, Hapus Rapat, Upload Rekaman, toggle kehadiran, assign dropdown, tombol tambah action item.

#### Polling Status Rekaman
- Diaktifkan (`pollingEnabled = true`) setelah user upload rekaman, atau jika saat halaman dibuka status masih dalam proses
- Polling `GET /meetings/:id/recording/status` tiap 3 detik
- Berhenti otomatis saat status `completed` atau `failed`

**Pipeline status rekaman:** `queued` → `transcribing` → `diarizing` → `extracting` → `sending_email` → `completed` / `failed`

---

### 7. Edit Rapat (`/meetings/[id]/edit`)
**File:** `app/(main)/meetings/[id]/edit/page.tsx`

Form pre-filled dari data rapat yang ada. Sama seperti form buat rapat tapi untuk update. Kirim `PATCH /meetings/:id`.

**Catatan:** Perubahan daftar peserta via form ini **tidak tersimpan** — ini adalah known bug di backend (`MeetingUpdate` schema tidak include `participant_emails`). Hanya field lain yang berubah.

---

### 8. Tugas Saya (`/action-items`)
**File:** `app/(main)/action-items/page.tsx`

Menampilkan semua action item yang **di-assign ke user yang sedang login**.

**Fungsi:**
- 3 stat card: Total / Aktif / Selesai
- Filter tab: Semua / Aktif / Selesai
- Search by nama tugas atau judul rapat
- Klik item → toggle status selesai/buka
- Urutan: Terlambat → Aktif → Selesai

**Perbedaan dengan action items di detail rapat:**
- Di sini: hanya tugas MILIK saya
- Di detail rapat: semua tugas untuk rapat itu, bisa di-assign ulang (organizer)

---

### 9. Profil (`/profile`)
**File:** `app/(main)/profile/page.tsx`

Update nama & info profil. Data disimpan ke `localStorage` (`user_profile`). Setelah simpan, dispatch event `profileUpdate` supaya navbar langsung refresh nama.

---

### 10. Check-In Portal (`/check-in/[token]`)
**File:** `app/check-in/[token]/page.tsx`

Halaman **publik** — tidak butuh login. Diakses via link magic yang dikirim ke email peserta.

**Fungsi:**
- Tampilkan info rapat: judul, jadwal, lokasi, nama peserta
- Tombol **"Check In Sekarang"** → konfirmasi kehadiran peserta
- Setelah AI selesai: tampilkan ringkasan rapat (tldr, keputusan, topik), action items, tombol **"Unduh PDF"**
- Action items bisa di-toggle status-nya (hanya open/done, tidak bisa assign dari sini)
- Token berlaku 24 jam setelah rapat berakhir. Kalau expired → tampilkan pesan error.

---

## API Functions (`lib/api.ts`)

Semua request HTTP ada di file ini. Axios instance sudah auto-attach JWT dari localStorage.

| Fungsi | HTTP | Endpoint | Keterangan |
|--------|------|----------|------------|
| `loginUser` | POST | `/auth/login` | Login, simpan token & profil |
| `registerUser` | POST | `/auth/register` | Daftar akun baru |
| `getMeetings` | GET | `/meetings` | List rapat (paginated + filter) |
| `searchMeetings` | GET | `/meetings/search` | Search rapat by keyword |
| `getMeeting` | GET | `/meetings/:id` | Detail satu rapat |
| `createMeeting` | POST | `/meetings` | Buat rapat baru |
| `updateMeeting` | PATCH | `/meetings/:id` | Update rapat |
| `deleteMeeting` | DELETE | `/meetings/:id` | Hapus rapat |
| `uploadRecording` | POST | `/meetings/:id/recording` | Upload file audio |
| `getRecordingStatus` | GET | `/meetings/:id/recording/status` | Cek status pemrosesan |
| `deleteRecording` | DELETE | `/meetings/:id/recording` | Hapus rekaman |
| `downloadNotulenPdf` | GET | `/meetings/:id/notulen.pdf` | Download PDF (blob) |
| `updateAttendance` | PATCH | `/meetings/:id/participants/:pid/attendance` | Update kehadiran |
| `updateActionItem` | PATCH | `/action-items/:id` | Toggle status / assign |
| `createActionItem` | POST | `/meetings/:id/action-items` | Tambah action item manual |
| `getMyActionItems` | GET | `/me/action-items` | Tugas milik saya |
| `getCheckin` | GET | `/check-in/:token` | Data halaman check-in |
| `confirmCheckin` | POST | `/check-in/:token/confirm` | Konfirmasi kehadiran |
| `updateCheckinActionItem` | PATCH | `/check-in/:token/action-items/:id` | Toggle action item (check-in) |
| `downloadCheckinNotulenPdf` | GET | `/check-in/:token/notulen.pdf` | Download PDF dari halaman check-in |

---

## React Query Hooks

| Hook | File | Kegunaan |
|------|------|----------|
| `useMeetings` | `hooks/useMeeting.ts` | List rapat + pagination |
| `useSearchMeetings` | `hooks/useMeeting.ts` | Search rapat |
| `useMeeting` | `hooks/useMeeting.ts` | Detail 1 rapat, cache key `["meeting", id]` |
| `useCreateMeeting` | `hooks/useMeeting.ts` | Mutasi buat rapat |
| `useUpdateMeeting` | `hooks/useMeeting.ts` | Mutasi edit rapat |
| `useDeleteMeeting` | `hooks/useMeeting.ts` | Mutasi hapus rapat |
| `useUpdateAttendance` | `hooks/useMeeting.ts` | Toggle kehadiran peserta |
| `useUploadRecording` | `hooks/useRecording.ts` | Upload file audio (ada progress) |
| `useRecordingStatus` | `hooks/useRecording.ts` | Polling status ML, aktifkan dengan `enabled` flag |
| `useDeleteRecording` | `hooks/useRecording.ts` | Hapus rekaman |
| `useMyActionItems` | `hooks/useActionItems.ts` | Tugas milik saya |
| `useUpdateActionItem` | `hooks/useActionItems.ts` | Toggle/assign action item |
| `useCreateActionItem` | `hooks/useActionItems.ts` | Tambah action item manual |

---

## Alur User (End-to-End)

### Alur 1: Organizer buat & jalankan rapat

```
1. Daftar akun (/register) → Login (/login)
2. Dashboard (/meetings) → klik "Buat Rapat"
3. Isi form → Submit → redirect ke /meetings/[id]
4. Backend kirim email undangan ke semua peserta
5. Setelah rapat selesai:
   - Organizer upload rekaman audio
   - Polling mulai tiap 3 detik
   - Progress tampil: queued → transcribing → diarizing → extracting → sending_email → completed
6. Setelah completed:
   - Ringkasan AI & transkrip muncul
   - Action items dari AI muncul
   - Organizer bisa assign action items ke peserta
   - Tombol PDF aktif
7. Backend otomatis kirim email notulen ke semua peserta
```

### Alur 2: Peserta check-in

```
1. Peserta terima email undangan berisi link check-in
2. Klik link → /check-in/[token] (tidak butuh login)
3. Halaman tampilkan info rapat + nama peserta
4. Klik "Check In Sekarang" → status kehadiran tercatat
5. Setelah rapat selesai & AI memproses:
   - Halaman menampilkan ringkasan, keputusan, action items
   - Peserta bisa unduh PDF notulen
   - Peserta bisa klik action item miliknya untuk tandai selesai
```

### Alur 3: User lihat tugas sendiri

```
1. Dari navbar → klik "Tugas Saya" (/action-items)
2. Lihat semua action item yang di-assign ke saya dari semua rapat
3. Filter: Semua / Aktif / Selesai
4. Search by nama tugas atau nama rapat
5. Klik item → toggle selesai / buka kembali
```

---

## Auth & Proteksi Halaman

- JWT token disimpan di `localStorage` (`access_token`) + cookie
- Middleware Next.js (`middleware.ts`) baca cookie untuk proteksi route
- Kalau token expired / 401 → axios interceptor auto hapus localStorage + redirect ke `/login`
- Halaman `(auth)/` → tidak butuh login
- Halaman `(main)/` → butuh login (dicek di middleware)
- `/check-in/[token]` → publik, tidak perlu login

---

## Known Issues (Bugs yang Belum Diperbaiki)

| Issue | Lokasi | Detail |
|-------|--------|--------|
| Edit peserta tidak tersimpan | `/meetings/[id]/edit` | Backend schema `MeetingUpdate` tidak include `participant_emails` |
| PDF download gagal di Firefox | `lib/api.ts` | `<a>` element tidak di-append ke DOM sebelum `.click()` |
| Assign action item tidak ada error feedback | `meetings/[id]/page.tsx` | `handleAssignTask` tidak punya error toast |
