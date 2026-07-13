# Frontend TODO: 3 field lokasi baru untuk notulen PDF (kampus format)

## Kenapa

Notulen PDF sekarang diubah supaya sesuai format resmi UDINUS. Salah satu section-nya (`2 LOKASI PERTEMUAN`) butuh breakdown lokasi yang lebih detail daripada field `location` yang sekarang (cuma teks bebas satu baris).

Backend sudah selesai: migration + model + schema + service sudah nambahin 3 kolom baru yang **opsional** (nullable) di tabel `meetings`:

| Field API (snake_case) | Label di form | Contoh isi |
|---|---|---|
| `location_building` | Gedung | "Gedung G Lantai 1" |
| `location_room` | Ruang | "Rapat G1" |
| `location_city` | Kabupaten/Kota | "Semarang" |

Field `location` yang lama **tetap dipakai apa adanya** (jadi jangan dihapus) — dia dipakai buat "Lokasi Pertemuan" versi ringkas di cover PDF & di halaman list/detail rapat seperti sekarang. 3 field baru ini cuma dipakai buat breakdown detail di section Lokasi Pertemuan pas PDF di-generate. Karena optional, kalau organizer nggak isi, PDF-nya bakal nampilin "-" — nggak bikin error apapun.

## Yang perlu diubah

### 1. `frontend/components/meetings/MeetingForm.tsx`

- Extend interface `MeetingFormInitialData` (baris ~13-22), tambah:
  ```ts
  locationBuilding?: string;
  locationRoom?: string;
  locationCity?: string;
  ```
- Tambah 3 field baru ke `formData` state (baris ~37-45), pakai `initialData?.locationBuilding ?? ""` dst sebagai default, sama seperti pola `location` yang sudah ada.
- Tambah 3 input teks baru di section "1. Detail Rapat" (deket field "Lokasi / Tautan Rapat" yang sudah ada di baris ~134-146). Semua optional, kasih helper text kecil semacam "Opsional — dipakai buat detail lokasi di PDF notulen resmi". Nggak perlu `required`.
- Di `handleSubmit` (baris ~68-86), tambahin ke `payload`:
  ```ts
  location_building: formData.locationBuilding || undefined,
  location_room: formData.locationRoom || undefined,
  location_city: formData.locationCity || undefined,
  ```

### 2. `frontend/app/(main)/meetings/[id]/edit/page.tsx`

Di `initialData` yang dilempar ke `<MeetingForm>` (baris ~59-68), tambahin mapping dari data meeting yang di-fetch:
```ts
locationBuilding: meeting.location_building ?? "",
locationRoom: meeting.location_room ?? "",
locationCity: meeting.location_city ?? "",
```

### 3. `frontend/lib/api.ts`

Tambahin 3 field optional ke inline type param di 2 fungsi:
- `createMeeting` (~baris 98-106)
- `updateMeeting` (~baris 111-121)
```ts
location_building?: string;
location_room?: string;
location_city?: string;
```

### 4. `frontend/types/index.ts`

Tambahin ke interface `MeetingDetail` (ada di sekitar baris 100-114, deket field `location: string | null` yang sudah ada):
```ts
location_building: string | null;
location_room: string | null;
location_city: string | null;
```
(Nggak perlu ditambahin ke `MeetingListItem` — nggak dipakai di halaman list.)

## Testing

1. Bikin/edit rapat, isi Gedung/Ruang/Kab-Kota, save.
2. Buka lagi halaman edit rapat itu — pastikan 3 field tadi ke-load balik (bukan kosong).
3. Kalau backend belum jalan migration-nya (`make migrate`), field-field ini bakal 404/500 pas dikirim — pastikan koordinasi sama Audi soal timing migration sebelum testing end-to-end.
