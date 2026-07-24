# Outline Presentasi: Kioku — Handoff ke Adik Tingkat (Versi Sederhana)

**Revisi:** versi sebelumnya kebanyakan istilah teknis (nama fungsi, jumlah endpoint, kata "transkrip"/"diarisasi"/"JWT"/dsb) — gak cocok buat audiens pemula. Versi ini dibuat ulang total: bahasa sehari-hari, tanpa jargon, tanpa kode.

**Struktur** (10 slide, urutan sudah ditentukan):
1. Cover
2. Masalah & Solusi
3. Peran Kita (tim)
4. Tech Stack (gabungan BE+FE+ML, dikasih keterangan)
5. FE
6. BE
7. ML
8. Peran Sistem (Organizer, User, Admin, Superadmin)
9. Cara Kerja Kioku
10. Penutup

---

### Slide 1: Cover
- Judul: **Kioku**
- 記憶 (kioku) — bahasa Jepang untuk "ingatan" (fun fact, bukan istilah teknis, aman dipakai)
- Tagline: "Aplikasi yang bikin rapat jadi lebih rapi — dari jadwal sampai catatan hasil rapat, semuanya otomatis."
- Dibangun oleh Audi, Helena, dan Azmi.

### Slide 2: Masalah & Solusi
Pasangan masalah → solusi, biar langsung kebayang manfaatnya:
| Masalahnya | Solusi Kioku |
|---|---|
| Absen masih manual, dicatat di kertas/Google Form terpisah | Peserta tinggal klik link buat absen, gak perlu login |
| Notulen sering gak ada, atau baru ditulis lama setelah rapat | Notulen otomatis jadi begitu rapat selesai |
| Tugas cuma diomongin, gak ada yang nyatet | Tugas otomatis kecatet dan diingetin ke orangnya |

### Slide 3: Peran Kita (Tim)
- **Audi — Backend**: ngurusin bagian yang gak keliatan tapi paling penting — nyimpen data, jaga keamanan, bikin semua fitur bisa jalan di belakang layar.
- **Helena — Frontend**: bikin tampilan web yang dipakai sehari-hari, biar gampang dan enak dipakai.
- **Azmi — Machine Learning**: bikin fitur AI-nya — yang ubah rekaman suara rapat jadi tulisan dan ringkasan otomatis.

### Slide 4: Tech Stack (gabungan, dikasih keterangan)
| Teknologi | Buat Apa | Bagian |
|---|---|---|
| Next.js | Bikin tampilan web | Frontend |
| FastAPI (Python) | Otak sistem di belakang layar | Backend |
| PostgreSQL | Tempat nyimpen semua data | Backend |
| Redis & Celery | Biar proses berat gak bikin web lemot | Backend |
| AI (OpenAI/Gemini) | Ubah suara jadi teks & bikin ringkasan | Machine Learning |
| AI Pengenal Suara | Nebak siapa yang lagi ngomong | Machine Learning |
| Docker | Biar semua bagian gampang dijalanin bareng | Semua bagian |

### Slide 5: FE (Frontend)
- Semua halaman yang dilihat & dipakai user — halaman rapat, check-in, profil — itu semua Frontend.
- Dipakein Next.js biar tampilannya cepat dan enak, di HP maupun laptop.
- Ada juga halaman khusus admin buat ngatur pengguna.

### Slide 6: BE (Backend)
- Nyimpen & ngatur semua data: rapat, peserta, tugas.
- Kirim email otomatis — undangan rapat dan notulen, gak perlu manual.
- Jaga keamanan — nentuin siapa boleh lihat/ubah apa.

### Slide 7: ML (Machine Learning)
- Suara jadi tulisan: rekaman rapat otomatis diubah jadi teks lengkap, gak perlu diketik manual.
- Ringkasan & tugas otomatis: teksnya diringkas dan tugas-tugas ikut kecatet, dibantu AI (ChatGPT/Gemini).
- Kenalan suara: ada AI yang bisa nebak siapa yang lagi ngomong — jalan di server sendiri, jadi lebih aman.

### Slide 8: Peran Sistem
Empat jenis pengguna, dijelasin rata (tanpa bedah teknis "global vs per-meeting" — itu yang bikin bingung sebelumnya):
- **User** — orang yang ikut rapat, bisa absen, terima notulen, dan lihat tugasnya sendiri.
- **Organizer** — yang bikin rapat, undang peserta, upload rekaman.
- **Admin** — bantu ngurus sistem, misal kalau ada akun yang bermasalah.
- **Superadmin** — admin paling atas, yang nentuin siapa aja yang boleh jadi admin.

### Slide 9: Cara Kerja Kioku
1. Bikin jadwal — organizer bikin rapat & undang peserta lewat email
2. Peserta absen — tinggal klik link, gak perlu login
3. Rapat direkam — audio diunggah setelah rapat selesai
4. Diubah otomatis — jadi teks, ringkasan, dan daftar tugas
5. Semua terkirim — notulen & tugas dikirim ke semua peserta

### Slide 10: Penutup
- "Kioku masih terus dikembangin — dan kalian bisa jadi bagian dari cerita selanjutnya."
- Kontak: Audi, Helena, Azmi.

---

## Catatan buat presenter
- Hindari istilah: JWT, bcrypt, endpoint, function signature, transkrip/diarisasi, cache key, dsb. Kalau perlu istilah teknis, jelasin pakai analogi sehari-hari (contoh: backend = "dapur restoran", frontend = "yang keliatan di meja").
- Kalau audiensnya ternyata lebih teknis dari perkiraan dan butuh detail lebih dalam (jumlah endpoint, arsitektur data, dsb.), versi lengkap sebelumnya (arsitektur 9-service, tabel endpoint, function signature ML, backlog peluang) masih ada di histori percakapan/artifact — tinggal minta dibikin ulang sebagai lampiran terpisah, gak perlu dicampur ke deck utama ini.
