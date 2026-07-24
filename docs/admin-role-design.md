# Desain Role Admin & Superadmin

**Status:** Keputusan desain sudah final lewat diskusi (18 Juli 2026), diperkuat lewat sesi *grilling* (20 Juli 2026) yang menambal beberapa gap — lihat catatan tambahan di tiap bagian. **Belum diimplementasikan** — dokumen ini cuma mencatat keputusannya, implementasi menyusul di PR terpisah.

## Kenapa

Saat ini `User` (`backend/app/models/user.py`) belum punya role sama sekali secara global — yang ada cuma role per-meeting lewat `MeetingParticipant` (organizer vs peserta), sesuai catatan "Auth Model" di `CLAUDE.md`. Dibutuhkan role admin karena dua kebutuhan konkret:

1. **User management** — suspend akun, reset password, dll.
2. **Audit & compliance lintas meeting** — admin perlu bisa mengecek data di luar meeting yang dia ikuti sendiri.

## Keputusan

### Level role

Dua tier: **`admin`** dan **`superadmin`**. Bukan role flat tunggal — pemisahan ini supaya gak semua admin bisa bikin admin baru sesuka hati.

### User management

| Kemampuan | Siapa yang punya |
|---|---|
| Bikin user baru manual | **Tidak ada** — tetap lewat form registrasi biasa |
| Edit profil user lain | **Tidak ada** |
| Suspend / unsuspend akun (soft, bukan hard delete) | Admin & superadmin |
| Hard delete user | **Belum dibangun** — sengaja ditunda |
| Reset password user (local auth) | **Superadmin only** |
| Promote / demote admin | **Superadmin only** |
| Cabut koneksi Google SSO/Calendar user lain | **Tidak ada** — di-drop, gak ada use case jelas (user sudah bisa self-service via `DELETE /auth/google/calendar`) |

**Aturan hierarki suspend/demote (ditambahkan 20 Juli 2026):**
- Admin **tidak boleh** suspend atau demote superadmin.
- Superadmin **tidak boleh** suspend atau demote superadmin lain jika aksi itu akan membuat jumlah superadmin aktif jadi nol ("proteksi superadmin terakhir"). Satu-satunya cara nambah superadmin kalau ini sampai kejadian adalah lewat seed script lagi, jadi harus dicegah di level aplikasi.
- Efek suspend harus real-time: status suspend dicek di setiap request terautentikasi (dependency `get_current_user`), bukan cuma sekali saat login. Ini juga otomatis membuat suspend berlaku untuk sesi yang login lewat Google SSO, tanpa perlu logika terpisah.

**Mekanisme reset password (ditambahkan 20 Juli 2026):** Superadmin memicu **email reset-link** (satu kali pakai, dikirim ke email terdaftar user) — bukan menentukan/mengetik password baru secara langsung. Superadmin tidak pernah tahu password final user; ini menjaga reset password sebagai murni alat bantu "lupa password", bukan alat impersonasi. Konsekuensinya:
- Untuk user yang akunnya terhubung Google SSO, reset password local **tidak** mengunci akses mereka (login Google tetap jalan) — kalau tujuannya benar-benar mengunci akses, gunakan **suspend**, bukan reset password.
- Notifikasi email ke user saat reset dipicu (mis. "password Anda direset, kalau bukan Anda hubungi...") **belum diputuskan** — didefer eksplisit ke PR terpisah, dicatat sebagai gap yang diketahui, bukan terlewat.

### Akses isi meeting (audit & compliance)

- **Default: metadata-only** untuk semua meeting di sistem — judul, waktu, organizer, daftar peserta, status kehadiran, status action item. Admin **tidak** otomatis bisa baca transcript/notulen/summary.
- Untuk baca isi (transcript/notulen/summary) meeting tertentu, admin mengisi alasan singkat lalu **langsung dapat akses saat itu juga** — **tidak ada approval gate** (dijuluki "Model 1" selama diskusi). Alasan yang diisi wajib tercatat di audit log.
  - Alternatif yang sempat dibahas dan **ditunda** (bukan dibatalkan): akses baru diberikan setelah di-approve superadmin ("Model 2"). Bisa direvisit kalau Model 1 terbukti kurang ketat di praktiknya.
  - **Akses tidak permanen** (ditambahkan 20 Juli 2026): admin harus mengisi alasan lagi **setiap kali** ingin membuka transcript/notulen/summary meeting yang sama — bukan sekali minta lalu akses terbuka selamanya untuk meeting itu. Ini biar tiap pembukaan konten benar-benar punya alasan tercatat sendiri, bukan cuma alasan pertama yang jadi izin seumur hidup.
  - **Tidak ada validasi kualitas** untuk field alasan (mis. minimal panjang karakter) — ini **risiko yang diterima sadar** untuk saat ini, didefer, bukan lupa. Artinya field alasan belum jadi kontrol nyata, baru formalitas pencatatan.
- **Rekaman audio mentah (dengar/download) permanen off-limits buat admin**, walaupun sedang dalam mode akses isi meeting. Akses isi cuma membuka teks transcript/notulen, gak pernah file audio asli. Alasan: suara itu data biometrik, teks sudah cukup buat keperluan compliance.

### Data yang tetap off-limits buat admin (walau role admin/superadmin)

- Password hash — gak pernah diexpose lewat API manapun (standar, bukan hal baru).
- Token OAuth Google (`GoogleCalendarCredential.access_token` / `refresh_token`, terenkripsi Fernet) — admin cuma boleh lihat status koneksi (connected/disconnected), gak pernah token ter-decrypt.
- File audio rekaman asli (lihat poin di atas).

### Audit log

Wajib ada, mencatat siapa-ngapain-kapan-kenapa untuk semua aksi sensitif: request akses isi meeting, suspend/unsuspend, promote/demote, delete meeting/recording.

Fitur export log ke file untuk laporan compliance **tidak dibutuhkan** saat ini.

**Siapa yang bisa baca log (ditambahkan 20 Juli 2026):**
- **Superadmin**: bisa baca seluruh log, semua actor.
- **Admin**: cuma bisa baca log di mana **dirinya adalah actor** (aksi yang dia lakukan sendiri) — bukan entri di mana dia jadi target/subjek dari aksi orang lain (mis. kalau admin itu sendiri pernah di-suspend, entri itu **tidak** muncul di log yang dia lihat).
- **Append-only**: tidak ada endpoint update/delete untuk audit log sama sekali — ini jaminan tamper-resistance-nya, bukan implisit tapi harus eksplisit gak ada endpoint-nya.
- **Review bersifat reaktif**, bukan proaktif/berkala — log baru benar-benar dibuka saat ada komplain atau kebutuhan mengambil bukti kasus tertentu, tidak ada jadwal audit rutin. Ini **risiko yang diterima sadar** demi kesederhanaan (bukan oversight): kalau tidak ada yang komplain, log soal insiden itu efektif tidak pernah dibaca siapa pun.

### Delete meeting/recording

Admin bisa hapus meeting/recording tertentu; aksi ini masuk audit log yang sama.

**Notifikasi ke peserta terdampak (ditambahkan 20 Juli 2026):** beda dari kebijakan baca-transcript (silent total), delete meeting/recording **menampilkan pesan generik** ke peserta yang terdampak (mis. "meeting ini dihapus oleh admin") — karena meeting yang hilang dari dashboard mereka bakal ketahuan sendiri, jadi lebih baik ada penjelasan singkat daripada peserta bingung tanpa konteks. Pesan ini generik, tidak perlu membocorkan alasan penghapusan.

### Notifikasi ke peserta

**Tidak ada notifikasi sama sekali** ke organizer/peserta saat admin **membaca isi** meeting mereka (transcript/notulen/summary) — sengaja, supaya gak "membocorkan" ke subjek investigasi bahwa meeting-nya sedang diperiksa. Kebijakan ini khusus untuk akses-baca; untuk **delete** meeting/recording, lihat bagian "Delete meeting/recording" di atas — beda kasus karena penghapusan otomatis terlihat oleh peserta.

### Bootstrap admin pertama

Admin/superadmin pertama dibuat lewat **seed script**, bukan lewat UI aplikasi (karena belum ada admin yang bisa mempromosikan siapa pun di awal).

### UI

Route terpisah **`/admin`** di frontend Next.js (mirip pola grup `(auth)` yang sudah ada) — bukan menempel di halaman dashboard biasa. Nav item ini cuma muncul kalau role user adalah admin/superadmin.

## Area yang akan tersentuh saat implementasi (belum dikerjakan)

- Migration + kolom role baru di `User` (dan kemungkinan tabel audit log baru).
- Endpoint admin di backend (user management, meeting audit view, request akses isi meeting, audit log).
- Dependency auth baru (semacam `get_current_admin_user` / `get_current_superadmin_user`).
- Seed script untuk admin pertama.
- Route group `/admin` + guard role di frontend.
- `get_current_user` perlu cek status suspend ke DB di **setiap request** (bukan cuma saat login) — bukan lagi murni validasi JWT signature/expiry.
- Guard "proteksi superadmin terakhir" di endpoint suspend & demote (tolak kalau aksi menyisakan nol superadmin aktif).
- Alur reset password via email reset-link (reuse infra email yang sudah ada untuk undangan meeting) — superadmin trigger, user yang set password baru sendiri.
- Query audit log perlu scoping: superadmin lihat semua baris, admin cuma baris `actor_id = current_user.id`.
- Endpoint request-akses-isi-meeting perlu re-submit alasan tiap kali (tidak ada tabel "grant" yang persist), jadi tiap pembukaan konten = satu baris log baru.
