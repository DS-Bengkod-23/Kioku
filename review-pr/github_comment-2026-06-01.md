## 🔍 Review: `feature/frontend-*`

**Reviewer:** Audi
**Tanggal:** 1 Juni 2026
**Status: ❌ Request Changes**

---

### Ringkasan

UI dan struktur folder sudah bagus secara visual, tapi **PR ini belum bisa di-merge** karena belum ada satu pun integrasi ke API backend. Semua data saat ini berjalan dari `localStorage` — artinya kalau backend jalan pun, frontend tidak akan connect.

Ada juga **1 bug compile-time** yang membuat app tidak bisa dibuka sama sekali.

---

### 🔴 Blocker

**App tidak bisa compile** — `lib/utils.ts` tidak ada, padahal di-import di `app/layout.tsx` dan beberapa komponen. Ini harus dibuat dulu sebelum yang lain bisa ditest.

**`lib/api.ts` tidak ada** — file ini adalah pusat semua komunikasi ke backend (axios instance + auth interceptor). Tanpa ini, tidak ada halaman yang bisa hit API.

**Tidak ada API call sama sekali** — login, register, create meeting, check-in, action items — semuanya pakai `localStorage` sebagai pengganti backend. Ini harus diganti semua ke endpoint yang sudah didefinisikan di `API_CONTRACT.md`.

**JWT auth tidak diimplementasikan** — login tidak menyimpan `access_token` dari response. Tidak ada mekanisme `Authorization: Bearer <token>` di request manapun.

---

### 🟡 Perlu Diperbaiki

**`types/index.ts` tidak sinkron dengan API Contract** — hanya ada 2 interface (`User`, `Meeting`) dan field-nya tidak match. Contoh: `Meeting` pakai `date + startTime` padahal API pakai `scheduled_at`. Interface untuk `Participant`, `ActionItem`, `Summary`, `Transcript`, `Recording`, `ProcessingStatus`, `AuthResponse`, `CheckInInfo` belum ada.

**Hooks adalah stub kosong** — `useMeetings` dan `useProcessingStatus` return hardcoded value, belum ada `useQuery` atau API call sama sekali. `QueryClientProvider` juga belum di-setup di `app/layout.tsx` padahal React Query sudah terpasang di `package.json`.

**Halaman `/meetings/[id]/recording` masih placeholder** — isinya 16 baris, hanya tampilkan ID parameter.

---

### ✅ Yang Sudah Oke

- Struktur folder sesuai spesifikasi README
- Routing Next.js App Router sudah benar (route groups, dynamic segments)
- UI semua halaman sudah ada dan tampilannya rapi
- Field di `MeetingForm` sudah match dengan API Contract (`title`, `location`, `scheduled_at`, `description`, `agenda_text`, `participant_emails`)
- Stack dasar (Next.js 14, Tailwind, shadcn) sudah benar

---

### Urutan Perbaikan yang Disarankan

```
lib/utils.ts → lib/api.ts → auth flow → types/index.ts → QueryClientProvider → hooks → ganti localStorage di semua halaman
```

Detail lengkap ada di `review-pr/review_frontend-2026-06-01.md`.
