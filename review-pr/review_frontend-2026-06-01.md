# Checklist Review Frontend — MeetMate
> Reviewer: Audi | Tanggal: 1 Juni 2026

---

### Ringkasan Eksekutif

Frontend yang dibuat Helena **belum siap** untuk diintegrasikan dengan backend. Struktur folder dan UI sudah ada, tetapi **semua fitur berjalan di localStorage** bukan dari API backend. Tidak ada satu pun API call yang diimplementasikan.

---

### BLOK A — API Layer (Wajib Dikerjakan Dulu)

- [ ] **A0. Buat `lib/utils.ts`**
  File ini tidak ada padahal di-import oleh `app/layout.tsx` dan beberapa komponen. App tidak bisa compile tanpa ini. Isi standar shadcn/ui:
  ```ts
  import { clsx, type ClassValue } from "clsx";
  import { twMerge } from "tailwind-merge";
  export function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
  }
  ```

- [ ] **A1. Buat `lib/api.ts`**
  File ini sama sekali tidak ada. Buat axios instance dengan:
  - `baseURL` dari `process.env.NEXT_PUBLIC_API_URL`
  - Request interceptor yang attach header `Authorization: Bearer <token>` dari localStorage/cookie
  - Response interceptor untuk handle error 401 (redirect ke `/login`)

- [ ] **A2. Implementasi auth flow yang benar di halaman Login**
  - Hit `POST /auth/login` dengan `{email, password}`
  - Simpan `access_token` dari response ke localStorage atau cookie
  - Redirect ke `/meetings` setelah sukses
  - Sekarang masih simulasi localStorage user profile, bukan hit API

- [ ] **A3. Implementasi auth flow yang benar di halaman Register**
  - Hit `POST /auth/register` dengan `{name, email, password}`
  - Redirect ke `/login` setelah sukses
  - Sekarang masih simulasi localStorage, bukan hit API

---

### BLOK B — TypeScript Types (Harus Sinkron dengan API Contract)

File `types/index.ts` sekarang hanya punya 2 interface yang tidak lengkap. Tambahkan semua type berikut sesuai `docs/API_CONTRACT.md`:

- [ ] **B1. Perbaiki interface `Meeting`** — field `date` + `startTime` harus jadi `scheduled_at`. Tambahkan: `location`, `status`, `agenda_text`, `organizer`, `participant_count`, `attendance_count`, `has_recording`, `processing_status`

- [ ] **B2. Tambah interface `Participant`** — `{id, email, name, role, attendance_status}`

- [ ] **B3. Tambah interface `Recording`** — `{id, file_url, duration, size, uploaded_at, processing_status}`

- [ ] **B4. Tambah interface `Segment`** dan `Transcript`** — segments array dengan `{speaker, start, end, text}`

- [ ] **B5. Tambah interface `Summary`** — `{id, tldr, decisions, topics}`

- [ ] **B6. Tambah interface `ActionItem`** — `{id, task, assignee, due_date, status, meeting?}`

- [ ] **B7. Tambah interface `ProcessingSteps`** dan `ProcessingStatusResponse`** — sesuai response `GET /meetings/:id/recording/status`

- [ ] **B8. Tambah interface `AuthResponse`** — `{access_token, token_type}`

- [ ] **B9. Tambah interface `CheckInInfo`** — `{meeting_title, scheduled_at, location, participant_name, already_checked_in}`

---

### BLOK C — Hooks (Wajib Diimplementasikan)

Kedua hooks sekarang isinya hardcoded stub, belum ada logic sama sekali.

- [ ] **C1. Implementasi `useMeetings.ts`**
  - Gunakan `useQuery` dari React Query
  - Hit `GET /meetings` dengan query params `page`, `limit`, `status`
  - Return `meetings`, `isLoading`, `error`, `pagination`

- [ ] **C2. Implementasi `useProcessingStatus.ts`**
  - Gunakan `useQuery` dengan `refetchInterval` (polling tiap 3–5 detik)
  - Hit `GET /meetings/:id/recording/status`
  - Hentikan polling otomatis kalau status sudah `completed` atau `failed`

- [ ] **C3. Setup `QueryClientProvider`**
  - React Query sudah terpasang di `package.json` tapi belum dipakai sama sekali
  - Wrap app di `app/layout.tsx` dengan `QueryClientProvider`

---

### BLOK D — Halaman & Komponen (Ganti localStorage → API)

- [ ] **D1. Halaman `/meetings` — ganti localStorage ke API**
  - Gunakan hook `useMeetings` untuk fetch dari `GET /meetings`
  - Search gunakan `GET /meetings/search?q=...`

- [ ] **D2. Halaman `/meetings/new` — ganti localStorage ke API**
  - `MeetingForm` submit harus hit `POST /meetings`
  - Handle response 201, lalu redirect ke `/meetings/:id`

- [ ] **D3. Halaman `/meetings/[id]` — ganti localStorage ke API**
  - Fetch data dari `GET /meetings/:id`
  - Tampilkan `transcript.segments`, `summary.tldr`, `summary.decisions`, `action_items` dari response API

- [ ] **D4. Komponen `AttendanceTable` — tambah action update manual**
  - Tambah tombol/action untuk organizer agar bisa hit `PATCH /meetings/:id/participants/:participant_id/attendance`
  - Request body: `{status: "hadir" | "tidak_hadir"}`

- [ ] **D5. Komponen `ActionItemList` — sambungkan ke API**
  - Toggle status harus hit `PATCH /action-items/:id` dengan `{status: "done"}`
  - Handle optimistic update atau refetch setelah mutasi

- [ ] **D6. Komponen `UploadZone` — implementasi upload sungguhan**
  - Hit `POST /meetings/:id/recording` dengan `multipart/form-data`
  - File field name: `file`
  - Format yang diterima: mp3, mp4, wav, m4a, max 200MB
  - Handle response 202 (bukan 200)

- [ ] **D7. Halaman `/action-items` — ganti localStorage ke API**
  - Fetch dari `GET /me/action-items` dengan query param `status` (optional)

- [ ] **D8. Halaman `/check-in/[token]` — sambungkan ke API**
  - Load info meeting dari `GET /check-in/:token`
  - Handle 404 jika token tidak valid/expired
  - Konfirmasi hadir hit `POST /check-in/:token/confirm`

---

### BLOK E — Halaman yang Masih Placeholder

- [ ] **E1. Implementasi halaman `/meetings/[id]/recording`**
  - Sekarang isinya cuma 16 baris placeholder, hanya tampilkan ID
  - Pindahkan `UploadZone` + `ProcessingStatus` ke sini (atau hapus duplikasi dari halaman detail)

---

### BLOK F — Minor / Nice to Have

- [ ] **F1. Tambah `.env.local`** — pastikan file ini ada dengan isi:
  ```
  NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
  ```

- [ ] **F2. Error handling global** — tampilkan pesan error dari format `{detail: "..."}` yang dipakai backend di semua form

- [ ] **F3. Protected routes** — pastikan halaman di `(main)` redirect ke `/login` kalau `access_token` tidak ada

---

### Urutan Pengerjaan yang Disarankan

```
A1 → A2 → A3 → C3 → B (semua) → C1 → C2 → D (semua) → E1 → F
```
Mulai dari API layer dulu sebelum ganti localStorage di komponen, supaya tidak bolak-balik.

---

**Total item:** 26 checklist | **Prioritas tinggi (blocker):** A1–A3, C1–C3, D1–D8
