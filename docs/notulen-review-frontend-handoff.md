# Handoff FE: Review Notulen oleh Organizer

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Dari:** Audi (Backend) · **Untuk:** Helena (Frontend)
**Status backend:** dikerjakan di branch `feature/backend-notulen-review` (rencana: [`notulen-review-backend-plan.md`](./notulen-review-backend-plan.md)). Kontrak di dokumen ini sudah final. Kamu bisa mulai FE begitu PR backend di-merge, atau lebih awal dengan menjalankan branch itu secara lokal (`make up`, lalu `make migrate`).

Alasan di balik setiap perilaku ("kenapa peserta tidak boleh lihat draft", "kenapa hapus audio tidak menghapus notulen") ada di [`notulen-review-design.md`](./notulen-review-design.md).

---

## 1. Apa yang berubah dari sisi pengguna

**Organizer:**
1. Setelah AI selesai memproses rekaman, notulen berstatus **Draft**. Belum ada email yang terkirim.
2. Organizer memeriksa dan mengedit ringkasan eksekutif, keputusan, topik, action item, dan nama speaker di transkrip.
3. Action item yang assignee atau tenggatnya gagal dicocokkan AI diberi tanda **"Perlu dicek"**.
4. Organizer klik **Publikasikan**. Email + PDF terkirim ke peserta sebagai **Versi 1**.
5. Setelah publish, organizer masih bisa mengedit. Perubahan langsung terlihat di web, tapi email baru dikirim kalau organizer klik **Kirim ulang notulen** (Versi 2, 3, dst.).

**Peserta:**
- Selama draft, peserta **tidak melihat apa pun** dari notulen: ringkasan, transkrip, action item, dan PDF. Yang tampil hanya "Notulen sedang ditinjau organizer."
- Setelah publish, peserta melihat notulen dengan label versi, plus "Diperbarui {tanggal}" kalau organizer mengedit setelah versi terakhir dikirim.

## 2. Perubahan perilaku endpoint lama (wajib di-handle)

1. **`processing_status === "completed"` tidak lagi berarti notulen sudah ada untuk peserta.** Artinya hanya "AI selesai memproses". Untuk semua keputusan tampilan notulen, pakai **`notulen.status`**.
2. **`sending_email` tidak akan muncul lagi** di `processing_status`. Urutannya sekarang `queued → transcribing → diarizing → extracting → completed`. Boleh dihapus dari `IN_PROGRESS_STATUSES` dan `PROCESSING_LABEL` (di detail meeting dan portal check-in).
3. **Untuk peserta selama draft**, `GET /meetings/{id}` mengembalikan `summary: null`, `transcript: null`, `action_items: []`. Hal yang sama berlaku untuk `PATCH /meetings/{id}/rsvp`, `GET /check-in/{token}`, `GET /me/action-items` (item dari meeting draft tidak ikut), dan pencarian.
4. **Hapus rekaman tidak lagi menghapus notulen.** Setelah `DELETE /meetings/{id}/recording`, `recording` bernilai `null` tapi `summary`, `transcript`, dan `action_items` tetap ada. Tombol PDF yang sekarang memakai syarat `processingStatus === "completed"` harus diganti menjadi `meeting.summary != null`.
5. **Upload rekaman pengganti** menghapus ringkasan dan action item hasil AI (termasuk hasil edit dan statusnya), lalu `notulen.status` menjadi `null` selama diproses dan `draft` setelah selesai.

## 3. Kontrak API

### Type baru dan yang berubah (`types/index.ts`)

```ts
export type NotulenStatus = "draft" | "published";

export interface NotulenMeta {
  status: NotulenStatus | null;     // null = belum ada notulen (belum upload / sedang diproses / gagal)
  current_version: number | null;   // versi terakhir yang dikirim ke peserta
  last_published_at: string | null; // ISO datetime pengiriman versi terakhir
  edited_at: string | null;         // ISO datetime terakhir organizer mengubah isi notulen
  has_unsent_changes: boolean;      // published + ada edit setelah versi terakhir dikirim
  needs_review_count: number;       // jumlah action item bertanda "Perlu dicek"
}

// ActionItemDTO — tambahan field
ai_assignee_text: string | null;  // nama assignee dari AI yang gagal dicocokkan, mis. "Pak Budi"
ai_due_date_text: string | null;  // tenggat dari AI yang gagal di-parse, mis. "Jumat depan"
needs_review: boolean;            // true kalau salah satu dari dua field di atas terisi

// MeetingDetail — tambahan field
notulen: NotulenMeta;

// MeetingListItem — tambahan field
notulen_status: NotulenStatus | null;

// Respons GET /check-in/{token} — tambahan field (type lokal di app/check-in/[token]/page.tsx)
notulen: NotulenMeta | null;
```

### Endpoint

Semua prefix `/api/v1` dan butuh `Authorization: Bearer <token>`.

| Method | Path | Siapa | Body | Response |
|---|---|---|---|---|
| PATCH | `/meetings/{id}/summary` | organizer | `{ tldr?: string; decisions?: string[]; topics?: string[] }` | `SummaryDTO` |
| PATCH | `/meetings/{id}/transcript/speakers` | organizer | `{ renames: Record<string, string> }` mis. `{ "SPEAKER_00": "Budi" }` | `TranscriptDTO` |
| POST | `/meetings/{id}/notulen/publish` | organizer | — | `NotulenMeta` |
| POST | `/meetings/{id}/notulen/resend` | organizer | — | `NotulenMeta` |
| PATCH | `/action-items/{id}` *(diperluas)* | organizer untuk field baru | field lama + `task?: string`, `dismiss_review?: true` | `ActionItemDTO` |
| DELETE | `/action-items/{id}` *(baru)* | organizer | — | `204` |

Catatan:
- **`PATCH /summary` bersifat parsial per field, tapi array dikirim utuh.** Untuk menghapus satu keputusan, kirim seluruh array `decisions` tanpa item itu. Item kosong atau berisi spasi saja dibuang backend.
- **Field "Perlu dicek" hilang sendiri** saat organizer mengisi assignee (menghapus `ai_assignee_text`) atau due date (menghapus `ai_due_date_text`). Tombol "Tandai sudah dicek" mengirim `{ "dismiss_review": true }`, yang menghapus keduanya.
- **Rename speaker tidak mengubah `edited_at`**, jadi tidak memicu "Ada perubahan yang belum dikirim". Edit ringkasan, keputusan, topik, dan action item (kecuali toggle status) memicunya.
- **Tidak ada endpoint untuk peringatan "Perlu dicek" saat publish.** FE yang menampilkan dialog berdasarkan `notulen.needs_review_count > 0`. Backend tidak memblokir publish.

### Error yang perlu ditampilkan

Tampilkan `detail` apa adanya lewat `extractApiError()`:

| Status | `detail` | Kapan |
|---|---|---|
| 403 | `Hanya organizer yang bisa mengedit notulen` | non-organizer memanggil endpoint edit/publish |
| 404 | `Notulen belum tersedia` | edit/publish sebelum AI selesai |
| 409 | `Notulen sudah dipublikasikan` | publish dua kali |
| 409 | `Notulen belum dipublikasikan` | kirim ulang saat masih draft |
| 409 | `Tidak ada perubahan sejak versi terakhir` | kirim ulang tanpa edit (mis. tombol diklik dua kali) |
| 409 | `Notulen sedang dikirim, muat ulang halaman` | dua publish bersamaan |
| 400 | `Speaker '{label}' tidak ada di transkrip` | rename label yang tidak ada |
| 422 | (validasi Pydantic) | `tldr` kosong, atau nama speaker baru kosong/lebih dari 100 karakter |

### Cache React Query

- Setiap edit ringkasan, speaker, publish, atau kirim ulang → invalidate `["meeting", id]`. Publish dan kirim ulang juga → `["meetings"]`.
- Setiap edit atau hapus action item → invalidate `["action-items"]` **dan** `["meeting", meetingId]` (aturan yang sudah ada di CLAUDE.md).

## 4. Teks UI

Pakai teks ini persis, supaya konsisten dengan email dan PDF dari backend.

| Tempat | Teks |
|---|---|
| Banner draft (organizer) | `Draft — belum terlihat oleh peserta. Periksa hasil AI lalu publikasikan.` |
| Tombol publish | `Publikasikan notulen` |
| Dialog publish, ada item perlu dicek | `Masih ada {n} action item yang perlu dicek. Tetap publikasikan?` · tombol `Periksa dulu` / `Tetap publikasikan` |
| Dialog publish, tanpa item perlu dicek | `Notulen akan dikirim ke semua peserta lewat email. Lanjutkan?` |
| Info published (organizer) | `Versi {n} · dikirim {tanggal}` |
| Ada edit belum terkirim (organizer) | `Ada perubahan yang belum dikirim ke peserta.` |
| Tombol kirim ulang | `Kirim ulang notulen` |
| Dialog kirim ulang | `Kirim versi {n+1} ke semua peserta? Email akan masuk ke thread notulen sebelumnya.` |
| Peserta, saat draft | `Notulen sedang ditinjau organizer.` |
| Peserta, saat published | `Versi {n}`, ditambah ` · Diperbarui {tanggal edited_at}` kalau `has_unsent_changes` |
| Badge di list meeting | `Draft` |
| Badge action item | `Perlu dicek` |
| Detail badge | `AI menyebut: {ai_assignee_text}` / `Tenggat dari AI: {ai_due_date_text}` |
| Tombol di action item | `Tandai sudah dicek` |
| Konfirmasi hapus action item | `Hapus action item ini?` |
| Konfirmasi hapus audio | `Hapus file audio? Notulen, transkrip, dan action item tetap tersimpan.` |
| Konfirmasi ganti rekaman (kalau `notulen.status` tidak null) | `Mengganti rekaman akan menghapus ringkasan dan action item hasil AI, termasuk hasil edit dan statusnya. Notulen kembali menjadi draft dan harus dipublikasikan ulang. Lanjutkan?` |
| Setelah publish | `Notulen dipublikasikan. Email sedang dikirim ke peserta.` |
| Setelah kirim ulang | `Versi {n} sedang dikirim ke peserta.` |

---

## 5. Tugas

Frontend belum punya test runner, jadi setiap tugas diverifikasi dengan `docker compose exec frontend npm run lint` ditambah pengecekan manual di browser yang tertulis di tugas itu. Login dengan dua akun: satu organizer, satu peserta (pakai jendela incognito untuk akun kedua).

### Task FE-1: Type, fungsi API, dan hooks

**Files:**
- Modify: `frontend/types/index.ts` (bagian 3)
- Modify: `frontend/lib/api.ts`: `updateSummary(meetingId, data)`, `renameSpeakers(meetingId, renames)`, `publishNotulen(meetingId)`, `resendNotulen(meetingId)`, `deleteActionItem(id)`; payload `updateActionItem` ditambah `task?` dan `dismiss_review?`
- Create: `frontend/hooks/useNotulen.ts`: `useUpdateSummary(meetingId)`, `useRenameSpeakers(meetingId)`, `usePublishNotulen(meetingId)`, `useResendNotulen(meetingId)`
- Modify: `frontend/hooks/useActionItems.ts`: `useDeleteActionItem(meetingId)`

- [ ] Implementasi sesuai kontrak dan aturan cache di bagian 3.
- [ ] `docker compose exec frontend npm run lint` → tanpa error.
- [ ] Commit: `feat(fe): notulen review types, API calls, and hooks`

### Task FE-2: Status notulen dan aksi publish di detail meeting

**Files:**
- Create: `frontend/components/notulen/NotulenStatusBar.tsx` (props: `notulen: NotulenMeta`, `isOrganizer: boolean`, `meetingId: string`)
- Modify: `frontend/app/(main)/meetings/[id]/page.tsx`

Perilaku:
- Organizer, `status === "draft"`: banner draft + tombol publish. Kalau `needs_review_count > 0`, dialog "perlu dicek"; selain itu dialog publish biasa.
- Organizer, `status === "published"`: `Versi {n} · dikirim {tanggal}`. Kalau `has_unsent_changes`, tampilkan teks "Ada perubahan..." dan tombol Kirim ulang aktif. Kalau tidak, tombol Kirim ulang **disabled**.
- Peserta: `status !== "published"` dan AI sudah selesai → `Notulen sedang ditinjau organizer.` Setelah published → label versi.
- Tombol PDF memakai syarat `meeting.summary != null`, bukan `processingStatus === "completed"`.
- Hapus `sending_email` dari `IN_PROGRESS_STATUSES` dan `PROCESSING_LABEL`.

- [ ] Implementasi.
- [ ] Lint lulus.
- [ ] Cek manual: skenario 1, 4, 6 di bagian 6.
- [ ] Commit: `feat(fe): notulen draft banner, publish and resend actions`

### Task FE-3: Edit ringkasan eksekutif, keputusan, dan topik

**Files:**
- Modify: `frontend/components/notulen/SummaryCard.tsx` (tambah mode edit, hanya untuk organizer, lewat prop `onSave?`)
- Modify: `frontend/app/(main)/meetings/[id]/page.tsx`

Perilaku:
- Tombol `Edit` hanya muncul untuk organizer.
- Mode edit: textarea untuk `tldr`; daftar keputusan dan topik yang bisa ditambah, diubah, dan dihapus per item.
- Simpan → satu `PATCH /summary` berisi seluruh array. Batal → kembali ke data terakhir.
- Tombol simpan disabled kalau `tldr` kosong (backend juga menolak dengan 422).

- [ ] Implementasi.
- [ ] Lint lulus.
- [ ] Cek manual: skenario 2.
- [ ] Commit: `feat(fe): edit executive summary, decisions, and topics`

### Task FE-4: Edit, hapus, dan "Perlu dicek" di action item

**Files:**
- Modify: `frontend/components/notulen/ActionItemList.tsx` (prop baru `onEditTask?`, `onDelete?`, `onDismissReview?`; data item ditambah `needsReview`, `aiAssigneeText`, `aiDueDateText`)
- Modify: `frontend/app/(main)/meetings/[id]/page.tsx` (mapping `actionItems` dan handler)

Perilaku (semua aksi baru hanya untuk organizer):
- Teks tugas bisa diedit inline. Simpan mengirim `{ task }`.
- Tombol hapus dengan konfirmasi `Hapus action item ini?`.
- Kalau `needs_review`: badge `Perlu dicek`, teks `AI menyebut: ...` dan/atau `Tenggat dari AI: ...`, dan tombol `Tandai sudah dicek`.
- Peserta tetap hanya bisa toggle status miliknya sendiri (perilaku lama).

- [ ] Implementasi.
- [ ] Lint lulus.
- [ ] Cek manual: skenario 2 dan 3.
- [ ] Commit: `feat(fe): edit, delete, and review flags on action items`

### Task FE-5: Ganti nama speaker di transkrip

**Files:**
- Modify: `frontend/components/notulen/TranscriptView.tsx` (prop `onRenameSpeakers?: (renames: Record<string, string>) => void`)
- Modify: `frontend/app/(main)/meetings/[id]/page.tsx`

Perilaku:
- Organizer melihat tombol `Ganti nama speaker`. Tombol itu membuka dialog berisi daftar label speaker unik dari transkrip, masing-masing dengan input nama baru.
- Simpan hanya mengirim label yang diubah. Nama baru tidak boleh kosong.
- Isi teks transkrip tidak bisa diedit.

- [ ] Implementasi.
- [ ] Lint lulus.
- [ ] Cek manual: skenario 2.
- [ ] Commit: `feat(fe): rename transcript speakers`

### Task FE-6: Badge Draft di list meeting

**Files:**
- Modify: `frontend/app/(main)/meetings/page.tsx`

Perilaku:
- Badge `Draft` kalau `notulen_status === "draft"`.
- `hasTranscript` memakai `m.notulen_status === "published"`, bukan `processing_status === "completed"`.

- [ ] Implementasi.
- [ ] Lint lulus.
- [ ] Cek manual: skenario 1 (badge muncul) dan 4 (badge hilang).
- [ ] Commit: `feat(fe): draft badge in meeting list`

### Task FE-7: Portal check-in peserta

**Files:**
- Modify: `frontend/app/check-in/[token]/page.tsx`

Perilaku:
- `notulenReady` memakai `meetingInfo.notulen?.status === "published"`.
- AI selesai tapi belum published → `Notulen sedang ditinjau organizer.`
- Published → label versi + `Diperbarui {tanggal}` kalau `has_unsent_changes`.
- Hapus `sending_email` dari daftar status dan label di file ini.

- [ ] Implementasi.
- [ ] Lint lulus.
- [ ] Cek manual: skenario 9.
- [ ] Commit: `feat(fe): check-in portal respects notulen review status`

### Task FE-8: Teks konfirmasi hapus audio dan ganti rekaman

**Files:**
- Modify: `frontend/app/(main)/meetings/[id]/page.tsx` (`handleDeleteRecording` dan alur upload pengganti)

Perilaku:
- Konfirmasi hapus audio memakai teks dari bagian 4.
- Saat organizer mengunggah rekaman baru dan `meeting.notulen.status` tidak `null`, tampilkan konfirmasi ganti rekaman sebelum upload dimulai.

- [ ] Implementasi.
- [ ] Lint lulus.
- [ ] Cek manual: skenario 7 dan 8.
- [ ] Commit: `feat(fe): clarify audio delete and recording replacement`

---

## 6. Skenario uji end-to-end

Email yang terkirim bisa dilihat di Mailhog: http://localhost:8025.

1. **Upload audio sampai selesai.** Organizer melihat banner Draft. Peserta melihat `Notulen sedang ditinjau organizer.`, tanpa ringkasan, transkrip, atau action item. Mailhog **kosong**. List meeting menampilkan badge `Draft`.
2. **Edit draft.** Ubah `tldr`, hapus satu keputusan, tambah topik, ubah teks satu action item, hapus satu action item, ganti `SPEAKER_00` menjadi nama orang. Refresh halaman → semua perubahan tetap ada.
3. **Peringatan "Perlu dicek".** Kalau ada action item bertanda `Perlu dicek`, klik Publikasikan → dialog peringatan muncul. Pilih `Periksa dulu` → tidak ada yang terkirim.
4. **Publish.** Mailhog menerima satu email per peserta. Peserta sekarang melihat notulen berlabel `Versi 1`. Badge Draft di list hilang.
5. **Edit setelah publish.** Organizer melihat `Ada perubahan yang belum dikirim ke peserta.` dan tombol Kirim ulang aktif. Peserta melihat `Versi 1 · Diperbarui {tanggal}`.
6. **Kirim ulang.** Mailhog menerima email kedua dengan subjek yang sama dan isi diawali "Versi 2". Label menjadi `Versi 2`, tombol Kirim ulang kembali disabled.
7. **Hapus audio.** Notulen, transkrip, dan action item tetap tampil. PDF masih bisa diunduh.
8. **Upload rekaman pengganti.** Dialog peringatan muncul. Setelah AI selesai, status kembali Draft dan peserta kembali melihat `sedang ditinjau`. Publish → `Versi 3`.
9. **Portal check-in peserta** (link dari email undangan): perilakunya sama dengan langkah 1, 4, dan 5.

Kalau ada respons API yang tidak sesuai dokumen ini, kabari Audi. Jangan menyesuaikan FE dengan perilaku yang berbeda dari kontrak.
