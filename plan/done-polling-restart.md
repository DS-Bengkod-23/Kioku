# Fix: Polling Restart Setelah Refresh

**Status:** DONE  
**File yang diubah:** `frontend/app/(main)/meetings/[id]/page.tsx`

---

## Masalah

`pollingEnabled` selalu dimulai dari `false`. Kalau user refresh halaman saat ML masih memproses (status `transcribing`, `diarizing`, dll), polling tidak aktif lagi — status tampak beku dan tidak update.

Polling hanya aktif lewat dua jalur lama:
- Upload berhasil → `setPollingEnabled(true)`
- Rekaman dihapus → `setPollingEnabled(false)`

Tidak ada yang menyalakan polling kembali saat data meeting pertama kali di-load.

---

## Fix (FE Only)

Tambah `useEffect` yang watch `meeting?.processing_status`. Saat data meeting selesai di-fetch (termasuk setelah refresh), jika status masih dalam state aktif, polling otomatis diaktifkan.

```typescript
useEffect(() => {
  if (["queued", "transcribing", "diarizing", "extracting", "sending_email"].includes(meeting?.processing_status)) {
    setPollingEnabled(true);
  }
}, [meeting?.processing_status]);
```

**Kenapa tidak perlu matikan polling manual saat selesai?**  
`useRecordingStatus` sudah punya `refetchInterval` yang return `false` otomatis saat status `completed` atau `failed` — polling berhenti sendiri tanpa perlu set `pollingEnabled(false)`.

---

## Tidak Ada Perubahan Backend / ML

Endpoint `GET /meetings/:id/recording/status` sudah mengembalikan `processing_status` dan `steps` yang dibutuhkan. Tidak ada contract yang berubah.

---

## Cara Verifikasi

1. Upload rekaman di halaman detail rapat, tunggu sampai status berubah ke `transcribing`
2. Refresh halaman
3. Status harus langsung polling dan menampilkan progress yang update setiap 3 detik
4. Saat status `completed` atau `failed`, polling berhenti otomatis
