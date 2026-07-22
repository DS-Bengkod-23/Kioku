# Handoff FE: Fitur Admin & Superadmin

**Dari:** Audi (Backend) · **Untuk:** Helena (Frontend)
**Status backend:** Semua 10 ticket sudah selesai diimplementasikan & dites di branch `backend` (commit-commit dengan prefix `feat:` tanggal 2026-07-20). Belum ada kerjaan frontend sama sekali — ini murni kontrak API buat kamu mulai dari sini.

Konteks keputusan desain ada di [`docs/admin-role-design.md`](./admin-role-design.md) kalau butuh alasan "kenapa" di balik suatu perilaku (misal kenapa alasan akses meeting harus diisi ulang tiap kali, atau kenapa admin gak bisa suspend admin lain).

---

## 1. Cara tahu role user yang login

`GET /api/v1/auth/me` (endpoint yang sudah ada) sekarang mengembalikan field baru **`role`**: `"user" | "admin" | "superadmin"`.

Ini yang dipakai buat guard nav item `/admin` — cuma muncul kalau `role !== "user"`. Gak perlu request tambahan.

## 2. Route group baru yang perlu dibikin

Sesuai desain doc: route terpisah **`/admin`** (mirip pola grup `(auth)` yang sudah ada), bukan nempel ke dashboard biasa.

Semua endpoint di bawah ini prefix `/api/v1/admin`, butuh header `Authorization: Bearer <token>` seperti biasa (bukan lewat cookie).

## 3. Endpoint contracts

### User management

| Method | Path | Role | Body | Response |
|---|---|---|---|---|
| GET | `/users` | admin, superadmin | — | `UserAdminResponse[]` |
| PATCH | `/users/{user_id}/suspend` | admin, superadmin | — | `UserAdminResponse` |
| PATCH | `/users/{user_id}/unsuspend` | admin, superadmin | — | `UserAdminResponse` |
| PATCH | `/users/{user_id}/role` | **superadmin only** | `{ "role": "user"\|"admin"\|"superadmin" }` | `UserAdminResponse` |
| POST | `/users/{user_id}/reset-password` | **superadmin only** | — | `202 { "detail": string }` |

```ts
type UserAdminResponse = {
  id: string; name: string; email: string;
  role: "user" | "admin" | "superadmin";
  suspended_at: string | null;  // ISO datetime, null = aktif
  created_at: string;
};
```

**UX yang perlu diperhatikan:**
- Suspend/unsuspend & promote/demote bisa balikin **403** kalau target-nya gak boleh disentuh oleh actor (mis. admin coba suspend admin lain, atau superadmin coba demote satu-satunya superadmin aktif yang tersisa). Tampilkan `detail` dari response error apa adanya — pesannya sudah jelas dalam Bahasa Indonesia.
- Reset password **tidak** langsung mengubah password — cuma mengirim email berisi link reset ke user. Jangan tampilkan seolah-olah password langsung berubah; tampilkan konfirmasi "email reset terkirim".
- Kalau target user itu akun Google-only (gak punya password lokal), reset-password akan **400** dengan pesan jelas — mungkin worth disable tombolnya di UI kalau kamu punya info `auth_provider` user itu (belum diexpose di `UserAdminResponse` sekarang — kalau butuh, bilang ke aku, gampang ditambahin).

### Audit & compliance meeting

| Method | Path | Role | Body | Response |
|---|---|---|---|---|
| GET | `/meetings` | admin, superadmin | — | `MeetingAdminResponse[]` |
| POST | `/meetings/{meeting_id}/access-requests` | admin, superadmin | `{ "reason": string }` | `MeetingContentAccessResponse` |
| DELETE | `/meetings/{meeting_id}` | admin, superadmin | — | `204` |
| DELETE | `/recordings/{recording_id}` | admin, superadmin | — | `204` |

```ts
type MeetingAdminResponse = {
  id: string; title: string; scheduled_at: string; status: string;
  organizer_name: string; organizer_email: string;
  participants: { name: string; email: string; role: string; attendance_status: string | null }[];
  action_items: { open: number; done: number };
  // metadata-only — gak ada transcript/summary/notulen di sini, itu memang sengaja
};

type MeetingContentAccessResponse = {
  meeting_id: string;
  transcript_segments: unknown[] | null;
  summary_tldr: string | null;
  summary_decisions: unknown[] | null;
  summary_topics: unknown[] | null;
  // TIDAK PERNAH ada field audio/recording di sini — itu permanen off-limits
};
```

**UX yang penting banget buat halaman "buka isi meeting":**
- Endpoint `access-requests` **wajib** diisi form alasan setiap kali admin mau buka transcript/notulen meeting, walaupun dia sudah pernah buka meeting yang sama sebelumnya. Jangan cache/simpan hasil `MeetingContentAccessResponse` dan tampilkan lagi tanpa request baru — desainnya sengaja begitu (tiap buka = 1 baris audit log baru). Form alasan gak ada validasi minimal panjang di backend, tapi kalau kamu mau kasih placeholder yang mendorong alasan yang bermakna, silakan.
- **Tidak ada** state "sudah pernah request akses" yang perlu disimpan di FE — treat setiap klik "buka isi meeting" sebagai request baru dari nol.
- Delete meeting/recording lewat endpoint admin ini **beda** dari delete yang organizer punya (`DELETE /api/v1/meetings/{id}` yang sudah ada) — punya organizer itu hard-delete permanen, punya admin ini soft-delete. Jangan disatukan tombolnya kalau kamu bikin UI organizer vs UI admin.

### Efek soft-delete ke endpoint meeting yang SUDAH ADA (breaking-ish, perlu di-handle)

`GET /api/v1/meetings/{meeting_id}` (endpoint peserta biasa, bukan admin) sekarang bisa mengembalikan **dua bentuk response berbeda**:

```ts
type MeetingDetailOrNotice =
  | MeetingDetail  // bentuk lama, gak berubah, kalau meeting normal
  | { id: string; deleted: true; message: string };  // BARU — kalau meeting di-soft-delete admin
```

**Kamu perlu cek `"deleted" in response`** (atau `response.deleted === true`) di halaman detail meeting sebelum coba render field-field `MeetingDetail` lainnya — kalau ketemu bentuk kedua, tampilkan `message`-nya sebagai notice, bukan crash karena field lain (`participants`, `organizer`, dst.) gak ada.

Selain itu, `MeetingListItem` (item di `GET /api/v1/meetings` list biasa) dapat **field baru additive**: `deleted_at: string | null`. Non-breaking — field lama semua tetap ada. Bebas dipakai buat badge "dihapus" di list view atau di-filter out, terserah kamu; backend sengaja gak menentukan perilaku list-view ini (cuma detail-view yang sudah diputuskan formatnya).

Juga: kalau **recording**-nya (bukan meeting-nya) yang di-soft-delete admin, `MeetingDetail.recording` dan `processing_status` bakal jadi `null` — sama seperti kalau memang belum ada rekaman sama sekali. Gak ada notice khusus buat kasus ini, cukup treat seperti "belum ada recording".

### Audit log

| Method | Path | Role | Query params | Response |
|---|---|---|---|---|
| GET | `/audit-logs` | admin, superadmin | `limit` (default 50, max 200), `offset` (default 0) | `AuditLogResponse[]` |

```ts
type AuditLogResponse = {
  id: string;
  actor_id: string | null;  // null kalau actor user-nya sudah dihapus (belum ada fitur hard-delete, jadi jarang kejadian)
  action: "suspend_user" | "unsuspend_user" | "promote_user" | "demote_user"
        | "reset_password" | "request_meeting_access" | "delete_meeting" | "delete_recording";
  target_type: string;  // "user" | "meeting" | "recording"
  target_id: string;
  reason: string | null;
  created_at: string;
};
```

**Penting:** response-nya **beda tergantung siapa yang login** — kalau yang login admin biasa, dia cuma dapat baris yang dia sendiri jadi actor-nya (gak bisa lihat aktivitas admin lain). Kalau superadmin, dapat semua baris. Ini murni logic backend, FE gak perlu ngapa-ngapain soal filtering — cukup render apa yang dibalikin.

## 4. Reset password confirm (bukan di bawah `/admin`, ini publik)

`POST /api/v1/auth/reset-password/confirm` — **tanpa auth**, dipanggil dari halaman publik `/reset-password/{token}` yang perlu kamu bikin (link-nya dikirim lewat email ke user, formatnya `{APP_BASE_URL}/reset-password/{token}`).

```ts
// Request
{ token: string; new_password: string }
// Response 200
{ detail: string }
// Response 400 kalau token invalid/expired/salah purpose
{ detail: string }
```

Halaman ini mirip alur "forgot password" standar — user input password baru 1x (atau 2x dengan confirm field, terserah kamu), submit, redirect ke `/login` kalau sukses.

## 5. Yang TIDAK perlu kamu bikin di FE (eksplisit di luar scope)

- Bikin user baru manual, edit profil user lain — endpoint-nya memang sengaja gak ada.
- Approval flow buat akses meeting (ditunda, "Model 2" di design doc) — akses langsung diberikan begitu form alasan disubmit, gak ada state "pending approval".
- Notifikasi apapun ke organizer/peserta saat admin baca isi meeting mereka — sengaja silent, jangan tambahin toast/notice di sisi peserta soal ini.
- Fitur export audit log ke file — belum dibutuhkan.

## 6. Kalau butuh field/endpoint tambahan

Backend-nya masih fresh, gampang ditambah kalau pas develop UI ketemu kebutuhan yang belum ke-cover di sini (contoh yang sudah kepikiran: field `auth_provider` di `UserAdminResponse` biar bisa disable tombol reset-password buat akun Google-only). Bilang aja ke Audi.
