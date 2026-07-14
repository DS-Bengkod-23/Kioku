# Draft Pull Request — frontend → main

Cara pakai: buka `https://github.com/audihus/MeetMate/compare/main...frontend`, klik "Create pull request", lalu copy judul dan body di bawah ini ke form-nya.

---

## Judul

```
feat(frontend): custom date/time picker di seluruh app, UX action items, presensi mandiri (nunggu BE)
```

---

## Body

```markdown
## Summary
- Semua input tanggal & waktu native browser (`<input type="date">` / `type="datetime-local">`) diganti komponen kalender custom (`DatePicker`), konsisten di seluruh aplikasi
- Action items: toggle status "Selesai" sekarang cuma lewat klik checkbox (bukan klik di mana pun pada baris), biar gak ke-toggle gak sengaja
- Fitur baru "Presensi Saya" — peserta bisa check-in lewat akun sendiri (tanpa magic link email) — **FE sudah siap, nunggu 1 perubahan kecil di backend, lihat bagian "Untuk Tim Backend"**
- Beberapa cleanup UX kecil di Action Items & Status Kehadiran

## Fitur Baru

### Komponen `DatePicker` custom (`frontend/components/notulen/DatePicker.tsx`, baru)
Kalender dropdown custom (grid Sen–Min, navigasi bulan, highlight hari ini/terpilih, tombol "Hari ini"), dipakai untuk menggantikan native date-picker browser yang tampilannya beda-beda tiap OS/browser dan kurang nyaman di beberapa user. Mendukung:
- `variant`: `"badge"` (trigger kecil inline, dipakai di baris action item) atau `"field"` (kotak input, dipakai di form)
- `withTime`: tambah pemilih jam:menit, dipakai di form jadwal rapat
- `allowClear`: sembunyikan tombol hapus untuk field wajib
- `fullWidth`: trigger melebar penuh mengikuti container

Dipasang di 4 tempat:
- Deadline action item (badge + form tambah manual) — `frontend/components/notulen/ActionItemList.tsx`
- Jadwal & Waktu Pelaksanaan di form Buat/Edit Rapat — `frontend/components/meetings/MeetingForm.tsx`
- Filter tanggal "Dari"/"Sampai" di Dashboard Rapat — `frontend/app/(main)/meetings/page.tsx`

### Toggle action item cuma lewat checkbox
Sebelumnya klik di mana pun pada baris action item (termasuk klik nama tugas) langsung menandai selesai — beresiko ke-toggle gak sengaja. Sekarang `onClick` cuma ada di tombol checkbox-nya.
- `frontend/components/notulen/ActionItemList.tsx` (di halaman detail rapat)
- `frontend/app/(main)/action-items/page.tsx` (halaman "Tugas Saya")

### Presensi Saya (self check-in) — FE selesai, nunggu BE
Card baru di halaman detail rapat, khusus untuk peserta yang login lewat akun sendiri (bukan organizer): tombol "Check In Sekarang" yang menandai diri sendiri hadir tanpa perlu buka link undangan dari email.
- `frontend/app/(main)/meetings/[id]/page.tsx` — card UI + handler
- `frontend/hooks/useMeeting.ts` — hook `useSelfCheckIn` (reuse endpoint `POST /check-in/{token}/confirm` yang sudah ada, tidak ada endpoint baru dari FE)

**Belum bisa berfungsi sampai backend berubah** — lihat bagian "Untuk Tim Backend" di bawah. Sudah ada toast fallback (`"Presensi mandiri belum tersedia untuk akunmu..."`) supaya tidak silent-fail kalau ada yang coba pakai sebelum backend siap.

## UX Cleanup
- Hapus legend caption "✓ = Tandai Hadir · ✗ = Tandai Tidak Hadir" di card Status Kehadiran (`frontend/components/meetings/AttendanceTable.tsx`) — dianggap redundan dengan ikon yang sudah ada
- Perbesar font & ikon assignee/deadline di baris action item (`text-xs`→`text-sm`, ikon 13px→15px) — sebelumnya kurang kebaca
- Validasi "Jadwal & waktu pelaksanaan wajib diisi" di form Buat/Edit Rapat (`MeetingForm.tsx`) — perlu ditambah manual karena atribut `required` bawaan hilang bareng native input yang diganti

## Untuk Tim Backend
Detail lengkap ada di `plan/backend-handoff-presensi-mandiri.md`. Ringkasnya: fitur "Presensi Saya" butuh satu perubahan kecil di `backend/app/routers/meetings.py` (`get_meeting`, baris 68-75) supaya peserta bisa lihat `checkin_token` miliknya sendiri — saat ini backend sengaja mengosongkan token **semua** peserta (termasuk milik sendiri) kalau yang minta bukan organizer.

## Test Plan
- [ ] Detail rapat → Action Items: klik "+ Deadline" / badge tanggal → kalender custom muncul, pilih tanggal auto-save, "Hapus deadline" berfungsi
- [ ] Detail rapat → Action Items: klik judul tugas / area kosong baris → status TIDAK berubah; klik checkbox → status berubah
- [ ] Tugas Saya (`/action-items`): sama seperti di atas — checkbox-only toggle
- [ ] Buat Rapat Baru: field "Jadwal & Waktu Pelaksanaan" pakai kalender custom + pemilih jam:menit, submit kosong → muncul pesan validasi
- [ ] Edit Rapat: field jadwal juga sudah pakai kalender custom (reuse `MeetingForm`)
- [ ] Dashboard Rapat: tombol "Tanggal" → filter "Dari"/"Sampai" pakai kalender custom, "Terapkan" filter hasil dengan benar
- [ ] Detail rapat sebagai peserta (bukan organizer): card "Presensi Saya" muncul, klik "Check In Sekarang" → saat ini akan muncul toast "belum tersedia" sampai fix backend di-deploy
- [ ] Status Kehadiran: pastikan legend text sudah tidak ada
```
