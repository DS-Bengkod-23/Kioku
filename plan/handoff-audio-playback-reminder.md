# Handoff FE → BE — Audio Playback & Reminder Action Item

**Tanggal:** 2026-07-19
**Branch:** `frontend`
**Status:** FE sudah dikerjakan (sebagian jalan penuh tanpa BE, sebagian nunggu endpoint baru). Dokumen ini nunjukin persis apa yang BE perlu lengkapi.

---

## Ringkasan

Dua fitur beda nasib:

1. **Audio playback** — FE **sudah dibangun lengkap** tapi **gak akan jalan** sampai BE bikin 1 endpoint baru. Tanpa endpoint itu, tombol "Putar Rekaman Asli" bakal selalu gagal (404/500).
2. **Reminder action item** — FE **sudah jalan penuh sekarang, mandiri, tanpa BE apapun** (notifikasi browser). Bagian BE di sini itu **pelengkap**, bukan blocker — nambah lapisan reminder yang lebih andal (email, tetap jalan walau app ketutup), bukan gantiin yang udah ada.

---

## Fitur 1: Audio Playback

### Kondisi Saat Ini (kenapa butuh endpoint baru)

`RecordingResponse.file_url` **bukan URL yang bisa diakses** — isinya cuma object key mentah MinIO, contoh `recordings/{meeting_id}/{uuid}.mp3` (lihat `backend/app/services/storage.py:31-33`, `upload_file()` return `object_key`, bukan URL). Dibuktikan juga dari `backend/app/tasks/process_recording.py:93` yang makein field itu ke `client.download_file(bucket, recording.file_url, tmp_path)` — jelas dipakai sebagai S3 key, bukan URL.

Gak ada fungsi presigned-URL di `storage.py`, dan gak ada endpoint streaming apapun sebelumnya.

### Kenapa didesain sebagai "proxy authenticated", bukan presigned URL

Ada 2 pendekatan umum buat expose file privat kayak gini:
- **Presigned URL** (browser hit MinIO langsung) — butuh MinIO reachable dari browser + CORS di sisi MinIO, dan `<audio src>` gak bisa nempelin header `Authorization`, jadi presigned URL jadi satu-satunya opsi kalau lewat jalur ini.
- **Proxy lewat backend yang sudah ada** (dipilih di sini) — endpoint baru yang di-protect JWT kayak endpoint lain, backend baca dari MinIO server-side terus stream balik ke FE. FE ambil pakai `axios` (bisa nempelin `Authorization` header seperti biasa) dengan `responseType: "blob"`, terus dikonversi ke object URL lokal buat dipasang ke `<audio src>` — **persis pola yang sudah dipakai** buat `downloadNotulenPdf()`/`downloadCheckinNotulenPdf()` di `frontend/lib/api.ts`.

Dipilih pendekatan kedua karena: gak perlu expose MinIO ke publik/browser sama sekali (tetap internal-only kayak sekarang), gak perlu setup CORS baru, dan konsisten sama pola auth yang sudah ada di semua endpoint lain.

### Scope BE

Endpoint baru:
```
GET /meetings/{meeting_id}/recording/audio
Authorization: Bearer <jwt>   (sama seperti endpoint meeting lain)

200 OK
Content-Type: audio/mpeg | audio/mp4 | audio/wav | audio/x-m4a  (sesuai ekstensi asli recording.file_url)
<binary body — bytes audio mentah, BUKAN JSON>

403 Forbidden  — bukan organizer maupun participant dari meeting ini
404 Not Found  — meeting tidak punya recording
```

Implementasi disaranin: baca object dari MinIO (`client.get_object(Bucket=..., Key=recording.file_url)`, sama polanya kayak `download_file` yang sudah dipakai di `process_recording.py`), lalu `StreamingResponse` balik ke client dengan `Content-Type` yang sesuai.

**Auth check:** sama persis kayak `get_meeting()` — cek `current_user` itu organizer ATAU salah satu participant meeting tersebut, kalau bukan keduanya → 403.

**Nice-to-have, bukan blocker:** dukungan HTTP `Range` request (`Accept-Ranges: bytes`) buat memungkinkan seeking tanpa download seluruh file dulu. FE versi sekarang **download seluruh file jadi blob** dulu (via `responseType: "blob"`) baru bisa diputar — cukup buat MVP, tapi utuk file sampai 200MB/2 jam (batas yang ada di `CLAUDE.md`), pengalaman "nunggu lama sebelum bisa play" bakal kerasa. Kalau ada waktu, Range support bikin FE bisa upgrade ke `<audio src="...">` langsung (streaming progresif) tanpa nunggu itu — tapi ini optimisasi lanjutan, gak perlu buat versi pertama jalan.

### Kontrak yang FE sudah asumsikan (jangan berubah tanpa kabar-kabar)

`frontend/lib/api.ts` — `getRecordingAudioBlobUrl(meetingId)` manggil persis endpoint di atas dengan `responseType: "blob"`. `frontend/components/recording/AudioPlayer.tsx` — lazy-load (baru fetch pas user klik "Putar Rekaman Asli", bukan otomatis pas halaman dibuka, karena filenya bisa besar). Dipasang di `frontend/app/(main)/meetings/[id]/page.tsx`, section "Rekaman Audio", tampil ke **organizer maupun participant** (bukan cuma organizer) begitu `meeting.recording` ada — terlepas dari `processing_status`-nya udah `completed` atau belum, karena dengerin rekaman mentah gak perlu nunggu transkripsi kelar.

### Cara Verifikasi

1. Meeting yang sudah punya recording → buka detail meeting sebagai organizer → section "Rekaman Audio" muncul → klik "Putar Rekaman Asli" → audio player browser muncul dan bisa diputar.
2. Login sebagai participant (bukan organizer) dari meeting yang sama → section yang sama juga muncul dan bisa diputar.
3. Login sebagai user yang **bukan** organizer/participant meeting itu (kalau ada cara akses ke halaman itu) → harus dapat 403 dari endpoint ini.
4. Meeting tanpa recording → section "Rekaman Audio" gak tampil sama sekali (FE sudah gate dengan `hasRecording`).

---

## Fitur 2: Reminder Action Item

### Yang sudah jalan sekarang (FE-only, tanpa BE apapun)

`frontend/hooks/useActionItemReminders.ts` + `frontend/components/ReminderBell.tsx` (dipasang di header utama, `app/(main)/layout.tsx`):

- Tombol lonceng di navbar — user klik sekali buat aktifin izin notifikasi browser (`Notification.requestPermission()`).
- Begitu izin aktif, hook ini cek `useMyActionItems("open")` (query yang **sudah ada**, gak ada endpoint baru) — kalau ada task yang due besok, hari ini, atau sudah lewat, muncul notifikasi browser sekali per task (di-dedupe pakai `localStorage`, gak akan spam berulang buat task yang sama).

**Batasannya, dan kenapa BE tetap dibutuhkan:** ini cuma jalan **selagi tab/app kebuka** di browser itu. Begitu tab ditutup atau device mati, gak ada reminder apapun yang nyampe. Ini bukan pengganti reminder proaktif yang beneran (misal email H-1), cuma lapisan tambahan.

### Scope BE (pelengkap, bukan blocker — sesuai draft di `plan/feature-ideas.md` #3)

1. Celery Beat scheduled task, jalan harian (misal jam 8 pagi).
2. Query `ActionItem` dengan `due_date = besok` dan `status = "open"`.
3. Kirim email reminder ke `assignee_participant.user.email` (kalau assignee-nya punya akun user; kalau cuma email peserta tanpa akun, kirim ke email participant-nya langsung) — pakai service email yang sudah ada (`services/email.py` / SMTP config yang sudah jalan buat undangan meeting).
4. Tambah kolom `reminder_sent_at` (nullable) di model `ActionItem` — supaya task yang due besok gak dikirimin reminder berkali-kali kalau Celery Beat-nya jalan lebih dari sekali per hari karena alasan operasional.
5. Template email baru: nama tugas, due date, link ke check-in portal (`/check-in/{token}`) atau halaman `/action-items` buat update status.

### Scope FE buat versi email ini

**Tidak ada.** Email dikirim otomatis dari BE, FE gak perlu render/trigger apapun — sama polanya kayak email undangan meeting yang sudah ada sekarang.

### Cara Verifikasi (bagian BE)

1. Bikin action item dengan `due_date` = besok, assign ke participant tertentu.
2. Jalanin Celery Beat task secara manual (atau tunggu jadwal harian-nya).
3. Cek Mailhog (`http://localhost:8025` di dev) — email reminder harus masuk ke inbox assignee.
4. Jalanin task itu lagi di hari yang sama → email **tidak** terkirim kedua kalinya (karena `reminder_sent_at` sudah keisi).

---

## Catatan

- Audio playback: **FE nunggu BE** — endpoint di atas satu-satunya yang bikin fitur ini jalan, semua kode FE sudah siap dan akan langsung berfungsi begitu endpoint itu live (gak perlu perubahan FE lagi).
- Reminder: **FE sudah jalan mandiri sekarang** — bagian BE di sini murni buat nambah lapisan yang lebih robust, boleh dikerjakan kapan aja tanpa ngeblock apapun di sisi FE.
