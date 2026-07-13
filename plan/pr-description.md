# Draft Pull Request — frontend → main

Cara pakai: buka `https://github.com/audihus/MeetMate/compare/main...frontend`, klik "Create pull request", lalu copy judul dan body di bawah ini ke form-nya.

---

## Judul

```
feat(frontend): kalender rapat, redesign dashboard, rebrand ke Kioku, bug fixes
```

---

## Body

```markdown
## Summary
- Fitur baru: halaman Kalender Rapat (`/calendar`) dan redesign hero + ringkasan statistik di Dashboard & Tugas Saya
- Rebrand nama aplikasi dari MeetMate menjadi Kioku, sekaligus penyegaran warna aksen (blue → indigo) di seluruh komponen
- Beberapa bug fix FE-only: PDF download gagal di Firefox, assign action item tanpa feedback error, form edit rapat salah include organizer, cache update meeting lambat refresh
- Dokumentasi handoff lengkap untuk tim backend di `plan/backend-handoff.md`

## Fitur Baru
- Halaman Kalender Rapat (`frontend/app/(main)/calendar/page.tsx`) — tampilan bulanan, klik tanggal untuk lihat rapat di hari itu
- Nav link "Kalender" di header dashboard
- Hero + ringkasan statistik (Total/Dijadwalkan/Selesai/Dibatalkan) di Dashboard Rapat
- Hero + ringkasan statistik (Total/Aktif/Selesai) di halaman Tugas Saya
- Action items sekarang di-sort berdasarkan due date (item tanpa due date ditaruh di akhir)

## Bug Fixes
- Fix PDF notulen gagal di-download di Firefox (`<a>` element di-append ke DOM sebelum `.click()`)
- Fix assign action item gagal tanpa feedback — sekarang ada toast error
- Fix form edit rapat yang salah menampilkan organizer di daftar "existing participant emails"
- Fix update meeting yang lambat ke-refresh di UI (pakai `setQueryData` bukan cuma `invalidateQueries`)

## Untuk Tim Backend
Detail lengkap ada di `plan/backend-handoff.md`. Ringkasnya:
- `POST /meetings/{id}/action-items` belum ada — FE sudah siap kirim, tombol tambah manual masih akan 404 (kontrak lengkap di `plan/done-action-items-improvements.md`)
- 3 bug aktif yang root cause-nya di backend, sudah dianalisis di `plan/pending-be-bugs.md` (due date action item read-only, search rapat by tanggal, layout PDF notulen)
- File baru `backend/.env.example` ditambahkan sebagai referensi — mohon dicek keakuratannya

## Test Plan
- [ ] Landing page (`/`) — cek nama "Kioku" tampil benar di navbar, hero, footer, FAQ, testimonial
- [ ] Login / Register / Forgot Password — cek logo "KIOKU" dan footer copyright
- [ ] Dashboard (`/meetings`) — cek hero + statistik, search, filter status, tombol "Tanggal" (masih placeholder)
- [ ] Kalender (`/calendar`) — cek grid bulan, navigasi bulan, klik tanggal menampilkan rapat yang benar
- [ ] Detail rapat (`/meetings/[id]`) — cek action items ter-sort by due date, assign action item, tombol "+ Deadline" (masih placeholder), download PDF
- [ ] Edit rapat (`/meetings/[id]/edit`) — cek organizer tidak muncul dobel di daftar peserta existing
- [ ] Tugas Saya (`/action-items`) — cek hero + statistik, filter, search
- [ ] Check-in portal (`/check-in/[token]`) — cek logo "Kioku" dan fungsi check-in/download PDF masih normal
```
