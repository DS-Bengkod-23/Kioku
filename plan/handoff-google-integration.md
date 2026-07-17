# Handoff FE ↔ BE — Integrasi Google (SSO Login + Calendar Sync)

**Tanggal:** 2026-07-17
**Branch:** `frontend`
**Status:** Planning/scoping — belum ada baris kode yang diubah. Dokumen ini dibuat supaya FE dan BE align dulu soal scope sebelum mulai implementasi.

---

## Ringkasan

Dua fitur terpisah tapi saling terkait, sama-sama butuh integrasi OAuth Google:

1. **Login pakai akun Google (SSO)** — alternatif buat email+password yang sudah ada.
2. **Sinkronisasi Google Calendar** — meeting di Kioku otomatis kebuat/keupdate/kehapus di Google Calendar user.

Keduanya bisa pakai **satu project Google Cloud** yang sama, tapi secara teknis independen — SSO cuma minta scope identitas (`openid email profile`), Calendar sync minta scope terpisah (`calendar.events`) yang jauh lebih sensitif karena butuh akses jangka panjang. **Rekomendasi: kerjakan SSO dulu**, baru Calendar sync — alasannya di bagian "Urutan Pengerjaan" di bawah.

---

## Kondisi Saat Ini (dicek langsung dari kode, 2026-07-17)

- **Tidak ada infrastruktur Google API sama sekali.** Dicek `.env`, `backend/app/config.py`, `frontend/package.json`, `backend/requirements.txt` — nihil `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET`, nihil library `googleapis`/`google-api-python-client`. `.env` cuma punya kredensial SMTP Gmail (`SMTP_USER`/`SMTP_PASSWORD`) buat kirim email undangan — itu integrasi berbeda, bukan Calendar API.
- **Auth model sekarang:** JWT + bcrypt, single global role. `backend/app/models/user.py:17` — `password_hash: Mapped[str] = mapped_column(String(255), nullable=False)`. Artinya **setiap user wajib punya password** — ini langsung relevan buat fitur SSO (lihat Fitur 1).
- **Role per-meeting:** `ParticipantRole` cuma `"organizer" | "peserta"` ([types/index.ts:7](../frontend/types/index.ts)), ditentukan dari `meeting.organizer_id == user_id` ([action_item.py:47](../backend/app/services/action_item.py)) — tidak relevan langsung ke fitur ini, dicatat sebagai konteks aja.

---

## Keputusan Arsitektur yang Belum Terjawab di Draft Awal

Ditemukan pas review ulang — ini harus disepakati BE **sebelum** mulai coding, bukan hal yang bisa nyusul belakangan:

1. **Sync API call gak boleh blocking request utama.** Project ini sudah punya Celery Worker (lihat service map di `CLAUDE.md`) buat kerja async. Panggilan ke Google Calendar API (insert/update/delete event) **harus** dijalankan lewat Celery task yang di-`.delay()` setelah `create_meeting()`/`update_meeting()`/`delete_meeting()` commit ke DB — bukan dipanggil sinkron di dalam request handler. Kalau sinkron, endpoint bikin-meeting Kioku jadi ikut lambat/gagal kalau Google API lambat/down, padahal itu gak ada hubungannya sama fungsi inti Kioku.
2. **Kegagalan sync harus non-blocking dan silent-safe.** `create_meeting()`/`update_meeting()` tetap harus **sukses** di Kioku meskipun push ke Google Calendar gagal (token expired, API down, dst) — log error-nya, tapi jangan bikin user gagal bikin meeting gara-gara integrasi pihak ketiga. Perlu disepakati juga: retry otomatis (berapa kali, pakai Celery retry) atau cukup log dan biarkan next update yang nyoba lagi.
3. **Jebakan Alembic enum yang sudah didokumentasikan di `CLAUDE.md`.** Kalau kolom `auth_provider` diimplementasi sebagai enum PostgreSQL, **wajib** ikuti pola yang sudah ditulis di `CLAUDE.md` bagian "Alembic + PostgreSQL enum pattern" — `postgresql.ENUM(...).create(op.get_bind(), checkfirst=True)` dulu di awal `upgrade()`, baru pakai `create_type=False` di `create_table()`/`add_column()`. Kalau pakai `sa.Enum()` biasa, migration bakal lempar `DuplicateObject`. Ini bukan hal baru — sudah kejadian sebelumnya di project ini makanya didokumentasikan, tinggal diikuti.
4. **Backfill meeting lama saat connect Calendar — direkomendasikan: TIDAK.** Waktu user pertama kali "Connect Calendar", default-nya cukup sync meeting **baru** ke depannya, bukan nyisir semua meeting lama dia dan push semua sekaligus (berisiko kena rate limit, dan meeting lama yang sudah lewat gak ada gunanya di-push). Kalau ternyata dibutuhkan, itu keputusan tambahan terpisah, bukan default.
5. **Redirect URI beda per environment.** Dev (`http://localhost:8000/...`) dan production (domain asli) butuh authorized redirect URI yang didaftarkan terpisah di Google Cloud Console — jangan asumsikan satu URI cukup buat semua environment.
6. **Butuh feature flag/kill-switch.** Project ini sudah punya pola env var switchable (lihat `LLM_PROVIDER` di `CLAUDE.md` — bisa ganti provider ML tanpa ubah kode). Ikuti pola yang sama: `GOOGLE_SSO_ENABLED` dan `GOOGLE_CALENDAR_SYNC_ENABLED` di `.env`, dicek di BE (sembunyikan endpoint/tombol terkait kalau `false`) dan di FE (sembunyikan tombol "Login with Google"/"Connect Calendar"). Tujuannya: kalau ada masalah di production (misal Google API berubah/kena rate limit/token bocor), bisa dimatiin lewat env var + restart container, tanpa harus revert deploy.

---

## Prasyarat Bersama (Setup Eksternal — Bukan Kode)

Sebelum FE atau BE bisa mulai kerja, perlu disiapkan di luar repo:

1. Buat project di [Google Cloud Console](https://console.cloud.google.com/), aktifkan **Google Calendar API** (kalau Calendar sync jadi dikerjakan) dan **Google Identity Services / OAuth consent screen** (buat SSO).
2. Setup OAuth consent screen — tentukan apakah app "Internal" (kalau organisasi pakai Google Workspace, bisa dibatasi ke domain tertentu) atau "External".
3. Register OAuth Client ID (tipe "Web application"), daftarkan authorized redirect URI(s) — akan beda antara flow SSO (biasanya cukup client-side, tanpa redirect URI server) dan Calendar sync (wajib redirect URI ke backend, misal `https://api.kioku.app/auth/google/calendar/callback`).
4. Hasilnya: `GOOGLE_CLIENT_ID` dan `GOOGLE_CLIENT_SECRET` — masuk ke `.env` backend. `GOOGLE_CLIENT_ID` juga dibutuhkan di sisi FE (client ID itu memang publik, aman ditaruh di `NEXT_PUBLIC_*`), `GOOGLE_CLIENT_SECRET` **tidak boleh** pernah masuk ke kode frontend.

### Checklist Env Var

| Variable | Dimana | Publik/Rahasia |
|---|---|---|
| `GOOGLE_CLIENT_ID` | `backend/.env` | Publik (boleh dipakai ulang di FE) |
| `GOOGLE_CLIENT_SECRET` | `backend/.env` | **Rahasia — backend only** |
| `NEXT_PUBLIC_GOOGLE_CLIENT_ID` | `frontend/.env.local` | Publik (sama nilainya dengan `GOOGLE_CLIENT_ID` di atas) |
| `GOOGLE_CALENDAR_REDIRECT_URI` | `backend/.env` | Beda nilai per environment (dev vs prod) — lihat poin 5 di "Keputusan Arsitektur" |
| `GOOGLE_TOKEN_ENCRYPTION_KEY` | `backend/.env` | **Rahasia** — dipakai buat enkripsi `access_token`/`refresh_token` tersimpan di DB (Fitur 2). Belum ada utilitas enkripsi di codebase sekarang — BE perlu pilih pendekatan (`cryptography.fernet` paling simpel) sebelum tabel token dibuat. |

**Siapa yang pegang ini:** perlu ditentukan siapa yang punya akses admin ke Google Cloud project organisasi — biasanya bukan Audi atau Helena langsung, kemungkinan perlu koordinasi ke pemilik akun Google organisasi (dosen pembimbing/institusi kalau ini proyek kampus, atau siapa pun yang jadi "owner" workspace).

---

## Fitur 1: Login dengan Google (SSO)

**Value:** memudahkan login, dan kalau organisasi pakai Google Workspace, deprovisioning otomatis (akun Google dicabut org → otomatis gak bisa login ke Kioku lagi) tanpa perlu admin panel manual.

**Effort:** Sedang di BE, Rendah di FE — SSO tidak perlu menyimpan token Google jangka panjang, cukup verifikasi sekali saat login lalu keluarkan JWT Kioku sendiri seperti biasa.

### Scope BE

1. **Migrasi skema `User`:**
   - Ubah `password_hash` jadi nullable (`backend/app/models/user.py:17`) — akun SSO-murni tidak punya password.
   - Tambah kolom `auth_provider` (`"local"` | `"google"`) dan `google_sub` (unique, ID unik dari Google — **jangan** pakai email sebagai identifier utama karena email bisa berubah/tidak unik selamanya).
2. **Endpoint baru** `POST /auth/google`:
   - Terima ID token dari FE (bukan authorization code — untuk SSO cukup ID token dari Google Identity Services).
   - Verifikasi signature ID token pakai public key Google (library `google-auth` Python sudah handle ini).
   - Cari user berdasarkan `google_sub`. Kalau belum ada → cek juga apakah ada user lama dengan email yang sama (dari signup password) → **ini keputusan yang harus disepakati dulu** (lihat "Keputusan yang Perlu Disepakati").
   - Keluarkan JWT dengan format **persis sama** seperti `POST /auth/login` yang sudah ada, supaya FE tidak perlu ubah apapun di sisi konsumsi token.
3. **(Opsional)** Pembatasan domain — kalau organisasi mau cuma email `@domain-tertentu` yang boleh SSO, validasi `hd` claim dari ID token.

### Kontrak API

```
POST /auth/google
Body:  { "id_token": "<ID token dari Google Identity Services>" }

200 OK
{ "access_token": "<jwt kioku>", "name": "..." }
# Bentuknya harus identik dengan response POST /auth/login yang sudah ada,
# supaya frontend/lib/api.ts loginUser() bisa dipakai ulang tanpa perubahan bentuk data.

400 Bad Request  — ID token tidak valid/expired
409 Conflict      — email sudah terdaftar via password, auto-link tidak diaktifkan
                     (lihat keputusan "Account linking" di bawah)
```

### Scope FE

1. Tombol "Login with Google" di `frontend/app/(auth)/login/page.tsx` dan `register/page.tsx`, pakai [Google Identity Services](https://developers.google.com/identity/gsi/web) (`<script src="https://accounts.google.com/gsi/client">`) dengan mode **popup/One Tap**, bukan full-page redirect.
   - **Kenapa popup, bukan redirect:** kalau pakai redirect penuh, butuh halaman callback baru yang harus didaftarkan ke `PUBLIC_PATHS` di `frontend/middleware.ts:4` (user belum punya cookie `access_token` pas di tengah proses OAuth, jadi middleware bakal nendang dia balik ke `/login` kalau route itu gak di-whitelist). Popup Google Identity Services menghindari masalah ini sama sekali karena seluruh redirect Google terjadi di popup terpisah, halaman Kioku sendiri gak pernah pindah dari `/login`.
2. Setelah dapat ID token dari popup Google, `POST` ke `/auth/google`, lalu proses response **persis** seperti alur `loginUser()` yang sudah ada ([lib/api.ts:39](../frontend/lib/api.ts)) — simpan `access_token` ke localStorage + cookie, redirect ke `/meetings`.
3. Tambah state error handling kalau Google gagal (popup ditutup, network error, dst) — reuse pattern `extractApiError`/`toast.error` yang sudah dipakai di halaman login sekarang.
4. **Catatan soal `user_profile` di localStorage:** alur login sekarang ([login/page.tsx:38-46](../frontend/app/(auth)/login/page.tsx)) membangun object `userSession` secara manual di client (termasuk field hardcoded kayak `role: "Team Member"` dan `joinDate` yang sebenarnya diisi tanggal hari ini, bukan tanggal join asli). Ini bug/tech-debt yang sudah ada sebelumnya, **di luar scope fitur ini** — tapi alur SSO harus tetap niru pola yang sama (bukan bikin bentuk baru) supaya halaman Profile gak crash baca `user_profile` yang beda struktur. Kalau mau dibenerin sekalian (idealnya ambil dari `GET /auth/me` beneran, bukan fabrikasi client-side), itu perlu dibahas terpisah — jangan digabung ke scope Google integration ini.

### Keputusan yang Perlu Disepakati (sebelum BE mulai coding)

- **Account linking:** kalau email X sudah daftar pakai password, terus coba "Login with Google" pakai email Google yang sama — auto-link ke akun yang sama, atau tolak dan minta user login manual dulu buat link secara eksplisit? (Auto-link berdasarkan email itu umum dilakukan karena Google selalu memverifikasi email, tapi tetap ini keputusan produk, bukan cuma teknis.)
- **Domain restriction:** perlu dibatasi ke domain tertentu, atau semua akun Google boleh?

### Cara Verifikasi

1. Registrasi baru pakai "Login with Google" dengan akun yang belum pernah dipakai di Kioku → user baru kebuat, bisa langsung akses `/meetings`.
2. Login pakai akun Google yang emailnya sama dengan akun password yang sudah ada → sesuai keputusan linking di atas.
3. Cek `GET /auth/me` balikin data user yang benar setelah login via Google.
4. Cek user hasil SSO **tidak bisa** login pakai form password kosong/asal (kalau `password_hash` mereka `null`).

---

## Fitur 2: Sinkronisasi Google Calendar

**Value:** meeting otomatis muncul di kalender pribadi user tanpa perlu klik manual "tambah ke kalender" tiap kali.

**Effort:** Tinggi — ini beban terbesar ada di BE karena harus menyimpan & mengelola token Google jangka panjang milik user (permukaan keamanan lebih besar dibanding SSO).

### Scope BE

1. **Tabel baru** buat kredensial per user, misal `google_calendar_credentials` (`user_id`, `access_token`, `refresh_token`, `token_expiry`, `scope`) — **wajib dienkripsi at-rest**, bukan plaintext, karena ini setara "kunci" ke kalender pribadi orang.
2. **Kolom baru** di `meetings`: `google_event_id` (nullable) — supaya update/cancel meeting bisa PATCH/DELETE event yang sudah ada, bukan bikin duplikat tiap kali ada perubahan.
3. **Endpoint OAuth terpisah dari SSO:**
   - `GET /auth/google/calendar/connect` — redirect ke consent screen Google dengan scope `calendar.events` (incremental authorization — user yang sudah login lewat cara apapun bisa "Connect Calendar" kapan saja, tidak harus bersamaan dengan login).
   - `GET /auth/google/calendar/callback` — tukar authorization code jadi access + refresh token, simpan ke tabel di atas.
   - `DELETE /auth/google/calendar` (disconnect) — hapus token tersimpan, hentikan sync.
4. **Hook sinkronisasi** di service yang sudah ada:
   - `create_meeting()` → insert event baru ke Calendar API, simpan `google_event_id` hasilnya.
   - `update_meeting()` → patch event yang sudah ada pakai `google_event_id` tersimpan.
   - `delete_meeting()` **dan** transisi status ke `cancelled` (`MeetingStatus.cancelled` di `backend/app/models/meeting.py:13`) → keduanya harus hapus event dari Calendar API, bukan cuma hard-delete. Cek titik mana status `cancelled` di-set (lewat `updateMeeting`/endpoint lain) dan pastikan hook-nya kepasang di situ juga, bukan cuma di path delete.
5. **Refresh token handling** — access token Google cuma hidup ~1 jam, perlu auto-refresh pakai `refresh_token` tersimpan sebelum tiap panggilan API.
   - **Kalau refresh gagal karena `invalid_grant`** (user revoke akses langsung dari halaman keamanan akun Google-nya, bukan lewat tombol Disconnect Kioku) — BE harus menangkap error spesifik ini dan otomatis set `connected = false` di tabel kredensial, bukan cuma log lalu diam. Tanpa ini, `GET /me/calendar-status` bakal terus bilang "Connected" padahal sync-nya diam-diam mati total.
6. **Fan-out ke siapa saja** — lihat keputusan di bawah, ini menentukan apakah sync hooks di atas loop ke satu user (organizer) atau semua participant yang sudah connect.
7. **Wajib lewat Celery, bukan sinkron** — sesuai poin 1 di "Keputusan Arsitektur" di atas. Task baru di `backend/app/tasks/`, misal `sync_meeting_to_calendar.delay(meeting_id, action="create"|"update"|"delete")`, dipanggil setelah commit di `meeting_service`, bukan dari dalam request handler-nya langsung.

### Kontrak API

```
GET  /auth/google/calendar/connect
→ 302 redirect ke consent screen Google (scope: calendar.events)

GET  /auth/google/calendar/callback?code=...&state=...
→ tukar code jadi token, simpan terenkripsi, lalu 302 redirect ke
  frontend (mis. /profile?calendar=connected atau ?calendar=error)

GET  /me/calendar-status
200 OK
{ "connected": true, "connected_at": "2026-07-17T10:00:00Z" }

DELETE /auth/google/calendar
200 OK
{ "connected": false }
```

### Scope FE

1. Section baru di `frontend/app/(main)/profile/page.tsx`: tombol "Connect Google Calendar" → redirect ke `/auth/google/calendar/connect`.
2. Indikator status koneksi, baca dari `GET /me/calendar-status` (hook baru, mis. `useCalendarStatus`) + tombol "Disconnect" yang manggil `DELETE /auth/google/calendar`.
3. Baca query param `?calendar=connected|error` pas halaman Profile dimuat (hasil redirect dari callback BE) → tampilkan `toast.success`/`toast.error` sesuai, lalu bersihkan query param dari URL (`router.replace`) biar gak nyantol pas di-refresh.
4. **Tidak perlu** UI baru per-meeting kalau sync-nya otomatis untuk semua meeting — tapi kalau BE putuskan sync-nya opsional per-meeting, perlu toggle tambahan di form create/edit meeting (`MeetingForm.tsx`).

### Keputusan yang Perlu Disepakati (sebelum BE mulai coding)

- **Arah sync:**
  - **Push-only** (Kioku → Google, direkomendasikan buat versi pertama): perubahan di Kioku otomatis terpush ke Google Calendar. Lebih sederhana, cukup dengan yang dijabarkan di atas.
  - **Bidirectional beneran** (Google → Kioku juga): kalau user geser jadwal langsung dari Google Calendar-nya, ikut keupdate balik di Kioku. Butuh lapisan tambahan — [Calendar API push notifications/webhook](https://developers.google.com/calendar/api/guides/push) + resolusi konflik. **Signifikan lebih berat**, sebaiknya jadi fase terpisah setelah push-only terbukti stabil, bukan dikerjakan sekaligus di awal.
- **Siapa yang di-sync:** cuma organizer, atau semua participant yang masing-masing sudah connect akun Google-nya sendiri? Kalau semua participant, BE perlu loop tiap peserta yang punya token tersimpan dan push event ke kalender masing-masing (dan skip diam-diam buat yang belum connect).
- **Isi event Calendar — field apa aja yang disertakan:**
  - `title`, waktu (`scheduled_at` + `duration_minutes`), `location` — jelas aman, ini info logistik biasa.
  - `description`/`agenda_text` — ini **konten rapat**, bukan cuma metadata. Perlu disepakati apakah ikut dimasukkan ke body event Google (artinya konten itu keluar dari infra self-hosted, mirip catatan privasi yang sudah ada di `CLAUDE.md` soal transcript/audio lewat cloud LLM) atau cukup judul+waktu+lokasi saja tanpa isi agenda.
  - **`attendees` (daftar participant) — rekomendasikan TIDAK diisi**, atau kalau diisi, set `sendUpdates: "none"` secara eksplisit di Calendar API. Kalau field ini diisi tanpa `sendUpdates: "none"`, Google otomatis ngirim email undangan/notifikasi **sendiri** ke semua participant — dobel dan bisa bikin bingung karena Kioku sendiri sudah punya alur email undangan lewat `email.py`.

### Cara Verifikasi

1. Connect akun Google dari halaman Profile → status berubah jadi "Connected".
2. Buat meeting baru → event otomatis muncul di Google Calendar user (cek judul, waktu, lokasi sesuai).
3. Edit jadwal/lokasi meeting itu di Kioku → event yang **sama** di Google Calendar ikut berubah (bukan event baru/duplikat — verifikasi `google_event_id` tetap sama).
4. Cancel/hapus meeting di Kioku → event terhapus dari Google Calendar.
5. Disconnect dari Profile → meeting berikutnya tidak lagi ke-sync, tapi meeting yang sudah pernah ke-sync tidak otomatis terhapus dari kalender (perlu disepakati juga apakah disconnect harus bersihin event lama atau dibiarkan).

---

## Urutan Pengerjaan yang Disarankan

1. **Setup Google Cloud project** sekali — dipakai ulang buat kedua fitur.
2. **SSO login dulu** — lebih ringan (tidak menyimpan token jangka panjang), sekaligus jadi validasi bahwa OAuth client & consent screen-nya sudah benar sebelum dipakai buat fitur yang lebih sensitif.
3. **Calendar sync (push-only)** menyusul, reuse project & consent screen yang sama, tinggal minta scope tambahan secara incremental.
4. **Bidirectional sync** (kalau beneran dibutuhkan) — fase terpisah, evaluasi dulu apakah push-only saja sudah cukup sebelum invest ke webhook + conflict resolution.

---

## Catatan

Dokumen ini hasil brainstorming FE, belum ada satu baris kode pun yang diubah untuk fitur ini. Semua estimasi "Scope BE" di atas adalah interpretasi FE berdasarkan baca kode yang ada — Audi perlu review dan sesuaikan dengan constraint yang mungkin belum kelihatan dari sisi FE (misal keterbatasan infra hosting, kebijakan penyimpanan data organisasi, dll) sebelum ini masuk sprint.
