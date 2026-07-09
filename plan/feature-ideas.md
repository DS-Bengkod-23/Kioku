# Feature Ideas — MeetMate Backlog

Ide fitur tambahan yang belum diimplementasikan, diurutkan dari effort rendah ke tinggi.

---

## Quick Wins (FE-only atau BE minimal)

### 1. Export Notulen ke PDF
**Owner:** FE  
**Effort:** Rendah  
**Value:** Tinggi — berguna untuk arsip formal atau dibagikan ke pihak luar yang tidak punya akun MeetMate

**Scope FE:**
- Tambah tombol "Download PDF" di halaman detail rapat (section ringkasan)
- Gunakan library seperti `jspdf` + `html2canvas`, atau `react-to-pdf`
- Konten: judul rapat, tanggal, daftar hadir, ringkasan AI, decisions, action items

**Scope BE:** Tidak ada

---

### 2. Reminder Otomatis Sebelum Rapat
**Owner:** BE  
**Effort:** Rendah-Medium  
**Value:** Tinggi — saat ini hanya ada email undangan saat rapat dibuat, tidak ada reminder kalau rapat dijadwal jauh hari

**Scope BE:**
- Tambah Celery Beat scheduled task yang jalan setiap jam
- Query semua meeting dengan `scheduled_at` dalam 24 jam ke depan yang belum di-remind
- Kirim email reminder ke semua peserta via `email.py` (template baru)
- Tambah field `reminder_sent_at` di `Meeting` model untuk tracking

**Scope FE:** Tidak ada (email otomatis dari BE)

---

### 3. Action Item Reminder ke Assignee
**Owner:** BE  
**Effort:** Rendah  
**Value:** Tinggi — tidak ada notifikasi sama sekali setelah notulen dikirim, assignee bisa lupa

**Scope BE:**
- Celery Beat task harian
- Query action items dengan `due_date = besok` dan `status = "open"`
- Kirim email reminder ke `assignee_participant.user.email`
- Template email: nama tugas, due date, link ke check-in portal untuk update status

**Scope FE:** Tidak ada

---

## Medium Effort

### 4. Speaker Labeling di Transkrip
**Owner:** FE + BE  
**Effort:** Medium  
**Value:** Tinggi — transkrip sekarang hanya tampil `SPEAKER_00`, `SPEAKER_01`, susah dibaca

**Cara kerja:**
- Organizer bisa map `SPEAKER_00` → nama peserta di UI
- Mapping disimpan di BE (field baru di Transcript atau tabel baru `SpeakerLabel`)
- FE: UI sederhana di tab Transkrip — dropdown per speaker untuk assign ke peserta
- Setelah di-map, nama peserta tampil menggantikan `SPEAKER_XX` di transkrip

**Scope BE:**
- Model/tabel `SpeakerLabel` (meeting_id, speaker_id, participant_id)
- Endpoint `PUT /meetings/{id}/transcript/speakers`

**Scope FE:**
- UI mapping di `TranscriptView.tsx`
- Tampilkan nama setelah mapping tersimpan

**Scope ML:** Tidak ada — diarization sudah jalan, hanya perlu mapping di level aplikasi

---

## Bigger Features

### 5. Dashboard Analytics Organizer
**Owner:** BE + FE  
**Effort:** Medium-Tinggi  
**Value:** Medium — insight untuk evaluasi tim

**Metrik yang ditampilkan:**
- Total rapat bulan ini vs bulan lalu
- Rata-rata tingkat kehadiran per rapat
- Action items: selesai vs pending (breakdown per assignee)
- Peserta yang paling sering absen

**Scope BE:** Endpoint agregasi baru `GET /me/analytics`  
**Scope FE:** Halaman baru `/analytics` atau widget di dashboard `/meetings`

---

### 6. Meeting Templates
**Owner:** BE + FE  
**Effort:** Tinggi  
**Value:** Medium — berguna untuk rapat yang strukturnya sama berulang (sprint review, 1-on-1, all-hands)

**Scope:** Organizer simpan template (judul, agenda, daftar peserta default) → bisa dipakai saat buat rapat baru

---

### 7. Recurring Meetings
**Owner:** BE + FE  
**Effort:** Tinggi  
**Value:** Medium  

**Scope:** Organizer set rapat sebagai recurring (weekly/biweekly/monthly) → sistem auto-generate meeting berikutnya setelah yang sekarang selesai

---

## Priority Ranking

| # | Fitur | Impact | Effort | Owner |
|---|-------|--------|--------|-------|
| 1 | Export PDF notulen | Tinggi | Rendah | FE |
| 2 | Reminder sebelum rapat | Tinggi | Rendah | BE |
| 3 | Action item reminder | Tinggi | Rendah | BE |
| 4 | Speaker labeling | Tinggi | Medium | FE + BE |
| 5 | Dashboard analytics | Medium | Medium | FE + BE |
| 6 | Meeting templates | Medium | Tinggi | FE + BE |
| 7 | Recurring meetings | Medium | Tinggi | FE + BE |
