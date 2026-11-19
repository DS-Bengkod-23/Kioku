# Desain: Review Notulen oleh Organizer (Human-in-the-Loop)

**Tanggal:** 2026-11-19 · **Status:** disepakati (sesi grilling Audi + Claude)
**Backend:** Audi → [`notulen-review-backend-plan.md`](./notulen-review-backend-plan.md)
**Frontend:** Helena → [`notulen-review-frontend-handoff.md`](./notulen-review-frontend-handoff.md) (berisi kontrak API lengkap)

---

## Masalah

Begitu pipeline ML selesai, ringkasan, keputusan, topik, dan action item hasil AI langsung dikirim lewat email + PDF ke semua peserta ([`process_recording.py`](../backend/app/tasks/process_recording.py) step 10). Kalau AI salah, versi yang salah sudah tersebar. Selain itu:

- Ringkasan eksekutif (`tldr`), keputusan, dan topik tidak bisa diedit sama sekali.
- Action item tidak bisa dihapus, dan teks tugasnya (`task`) tidak bisa diedit.
- Kalau nama assignee atau tenggat dari AI tidak cocok (mis. "Pak Budi", "Jumat depan"), nilainya **dibuang diam-diam**. Organizer tidak pernah tahu AI sempat menyebutnya.

## Tujuan

Organizer memeriksa dan memperbaiki hasil AI **sebelum** peserta melihat apa pun, dan tetap bisa memperbaikinya setelah notulen dikirim.

## Keputusan

| # | Keputusan | Alasan singkat |
|---|---|---|
| 1 | Hasil AI menjadi **draft**. Email + PDF baru dikirim saat organizer klik **Publikasikan**. | Edit setelah email terkirim bukan human-in-the-loop, itu koreksi setelah kejadian. |
| 2 | Selama draft, peserta **tidak melihat apa pun** (ringkasan, transkrip, action item, PDF, hasil pencarian). Reminder action item tidak dikirim. | Action item yang belum diverifikasi bisa salah assignee, dan orang bisa langsung mengerjakannya. |
| 3 | Yang boleh edit dan approve **hanya organizer** (`meeting.organizer_id`). Admin/superadmin tidak bisa edit. | Tidak perlu role baru. Akses admin ke konten dirancang read-only + justifikasi. |
| 4 | Setelah publish masih **boleh diedit**, tanpa kirim ulang otomatis. Ada tombol manual **Kirim ulang notulen**. | Kesalahan yang baru ketahuan belakangan tetap bisa diperbaiki, tanpa spam email setiap simpan. |
| 5 | Email kirim ulang masuk ke **thread email pertama** dan diberi label **"Versi N"**. | Email lama di inbox tidak bisa dihapus (SMTP tidak punya recall). Thread + label paling mendekati "cuma satu email". |
| 6 | Tabel **`notulen_versions`**: snapshot setiap kali notulen dikirim (`kind=published`, bernomor) + snapshot hasil AI asli setiap pemrosesan (`kind=ai`, tanpa nomor). | Riwayat isi yang dikirim + bahan evaluasi ML (seberapa sering dan di mana AI dikoreksi). |
| 7 | Rekaman **boleh diganti kapan saja**. Kalau diganti setelah publish, notulen kembali ke draft dan diterbitkan sebagai versi berikutnya. Hasil edit dan status action item dari AI hilang (dengan peringatan). **Hapus audio tidak menghapus notulen.** | Fleksibel untuk kasus salah file atau rekaman terpotong. Hapus audio dipisah supaya notulen resmi tidak hilang karena alasan privasi. |
| 8 | Yang bisa diedit: ringkasan eksekutif, keputusan, topik, action item (tambah/edit task/assignee/due date/**hapus**), dan **nama speaker** di transkrip. Isi teks transkrip tidak bisa diedit. | Edit teks transkrip tidak memperbarui ringkasan, jadi hanya kerja tanpa efek. |
| 9 | Penanda **"Perlu dicek"** pada action item yang assignee atau due date-nya gagal dicocokkan, sambil menampilkan teks asli dari AI. | Organizer tahu bagian mana yang paling mungkin salah. |
| 10 | Tidak ada email pemberitahuan ke organizer. Cukup **tanda "Draft"** di tampilan. Tidak ada auto-publish. | Auto-publish meniadakan human-in-the-loop. |
| 11 | Status disimpan di **`meetings.notulen_status`**, bukan di `Recording`. Email publish dikirim lewat **Celery task**. | Status tidak boleh hilang saat audio dihapus. Kirim ke banyak peserta tidak boleh membuat request lama. |
| 12 | Kalau masih ada item "Perlu dicek", publish **hanya memberi peringatan**, tidak diblokir. | Assignee kosong bisa sah (tugas untuk orang di luar daftar peserta). |
| 13 | Meeting lama yang sudah punya `Summary` di-backfill menjadi **published v1** tanpa snapshot AI. | Notulen lama sudah terkirim. Action item-nya mungkin sudah diedit, jadi bukan hasil AI murni. |

## Siklus status notulen

```
(null) ──pipeline selesai──▶ draft ──publish──▶ published (versi 1)
                                                    │
                     edit oleh organizer ───────────┤  has_unsent_changes = true
                                                    │
                     kirim ulang ──────────────────▶ published (versi n+1)

ganti rekaman (status apa pun) ──▶ (null, sedang diproses) ──pipeline──▶ draft ──publish──▶ versi n+1
hapus audio ──▶ status tidak berubah, notulen tetap
```

- `notulen_status = null` berarti belum ada notulen (belum ada rekaman, sedang diproses, atau gagal).
- Nomor versi **hanya naik saat notulen dikirim** (publish atau kirim ulang), bukan setiap kali disimpan.
- Publish setelah ganti rekaman memakai nomor lanjutan (n+1), bukan kembali ke 1.

## Model data

| Perubahan | Tipe | Keterangan |
|---|---|---|
| `meetings.notulen_status` | enum `notulenstatus` (`draft`, `published`), nullable | Status editorial notulen |
| `meetings.notulen_edited_at` | `timestamptz`, nullable | Waktu terakhir organizer mengubah isi notulen (ringkasan/keputusan/topik/action item). Toggle status action item dan rename speaker **tidak** dihitung. |
| tabel `notulen_versions` | baru | `id`, `meeting_id` (FK cascade), `kind` enum `notulenversionkind` (`ai`, `published`), `version` int nullable (null untuk `ai`), `content` JSONB, `created_by` (FK users, set null; null untuk `ai`), `created_at`. Unique `(meeting_id, version)`. |
| `action_items.ai_assignee_text` | `text`, nullable | Nama assignee dari AI yang **gagal** dicocokkan ke peserta |
| `action_items.ai_due_date_text` | `text`, nullable | Teks tenggat dari AI yang **gagal** di-parse sebagai tanggal ISO |

Turunan (dihitung, tidak disimpan):

- `needs_review` (per action item) = `ai_assignee_text` atau `ai_due_date_text` tidak null.
- `current_version` = `version` terbesar dengan `kind=published`. `last_published_at` = `created_at` baris itu.
- `has_unsent_changes` = status `published` **dan** `notulen_edited_at > last_published_at`.

Penanda "Perlu dicek" hilang kalau organizer mengisi assignee (menghapus `ai_assignee_text`), mengisi due date (menghapus `ai_due_date_text`), atau menekan "Tandai sudah dicek" (menghapus keduanya).

### Isi snapshot (`content`)

```jsonc
// kind = "published"
{ "tldr": "...", "decisions": ["..."], "topics": ["..."],
  "action_items": [{ "id": "uuid", "task": "...", "assignee_participant_id": "uuid|null",
                     "assignee_name": "string|null", "due_date": "YYYY-MM-DD|null" }] }

// kind = "ai" — output ML apa adanya, sebelum dicocokkan ke peserta
{ "tldr": "...", "decisions": ["..."], "topics": ["..."],
  "action_items": [{ "task": "...", "assignee_name": "string|null", "due_date_text": "string|null" }] }
```

## Aturan visibilitas

Notulen **terlihat** oleh seorang user kalau dia organizer meeting itu, **atau** `notulen_status = published`. Kalau tidak terlihat, setiap jalur di bawah wajib menyembunyikan isinya:

| Jalur | Perilaku saat tidak terlihat |
|---|---|
| `GET /meetings/{id}` | `summary`, `transcript` = `null`, `action_items` = `[]`. Field `notulen` (status/versi) tetap dikirim. |
| `GET /meetings/{id}/notulen.pdf` | 404 `"Notulen belum tersedia"` |
| `GET /meetings/search` | Kecocokan di `tldr` atau `task` diabaikan. Kecocokan judul tetap berlaku. |
| `GET /check-in/{token}` | `summary` = `null`, `action_items` = `[]` |
| PDF di portal check-in | 404 |
| Ubah status action item via portal check-in | 404 |
| `GET /me/action-items` | Item dari meeting yang belum published tidak ikut |
| `PATCH /action-items/{id}` oleh assignee non-organizer | 404 |
| Reminder action item (celery-beat) | Item dari meeting yang belum published dilewati |

Akses admin ke konten meeting (`POST /admin/meetings/{id}/access-requests`) **tidak** diubah: admin tetap bisa melihat draft dengan justifikasi yang tercatat di audit log.

## Email dan versi

- Subjek selalu `Notulen Rapat: {judul}` supaya klien email menggabungkannya ke satu thread.
- Message-ID root per peserta bersifat deterministik: `<notulen-{meeting_id}-{participant_id}@{domain}>`. `domain` = bagian setelah `@` dari `SMTP_USER`, atau `kioku.local` kalau kosong. Tidak ada setting baru.
- Versi 1: `Message-ID` = root. Versi ≥ 2: `Message-ID` baru (unik), `In-Reply-To` dan `References` = root.
- Isi email versi ≥ 2 diawali `Versi {n} — versi ini menggantikan notulen sebelumnya.`
- Label versi di PDF: draft → `DRAFT — belum dipublikasikan`; published → `Versi {n}`, ditambah `· diperbarui {dd/mm/yyyy}` kalau `has_unsent_changes`.
- Email dikirim ke setiap peserta yang punya invitation token (sama seperti sekarang), lewat Celery task `send_notulen_task`.

## Perubahan perilaku yang sudah ada

- Pipeline tidak lagi membuat PDF atau mengirim email. Urutan status menjadi `queued → transcribing → diarizing → extracting → completed`. Nilai enum `sending_email` tetap ada di database tapi tidak dipakai lagi.
- Kunci absensi dan `meeting.status = completed` tetap terjadi di akhir pipeline, tidak menunggu publish.
- `DELETE /meetings/{id}/recording` hanya menghapus file audio dan baris `Recording`. Transkrip, ringkasan, action item, dan status notulen tetap ada.
- Upload rekaman pengganti tetap menghapus transkrip, ringkasan, dan action item dari AI (perilaku lama), lalu mengosongkan `notulen_status`. Riwayat `notulen_versions` tidak dihapus.
- `PATCH /action-items/{id}` kini bisa mengubah `task` (organizer saja).

## Di luar cakupan (ditunda)

- Transkrip di samping editor dengan pemutar audio.
- Tautan dari setiap keputusan/action item ke potongan transkrip sumbernya (butuh perubahan output ML yang statusnya *frozen*, harus dikoordinasikan dengan Azmi).
- Role notulis yang ditunjuk organizer.
- Tampilan riwayat versi dan diff v0 vs v1 di UI (datanya sudah disimpan).
- Merapikan event Google Calendar atau menyimpan status action item saat rekaman diganti setelah publish.

## Risiko yang diketahui

- **Meeting hasil backfill:** email v1-nya terkirim sebelum fitur ini, tanpa Message-ID root. Kirim ulang v2 untuk meeting itu akan muncul sebagai thread baru.
- **Judul meeting diganti** di antara versi: Gmail memecah thread karena subjek berbeda.
- **Ganti rekaman setelah publish:** status `done` dan reminder pada action item dari AI hilang. Organizer diperingatkan di dialog konfirmasi.
- **Gmail via SMTP** biasanya mempertahankan Message-ID dari klien, tapi ini harus diverifikasi sekali dengan akun Gmail sungguhan (lihat checklist di rencana backend).
