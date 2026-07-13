# Action Items Improvements

**Status:** FE DONE — BE endpoint belum ada (lihat bagian dependensi)  
**File yang diubah:**
- `frontend/lib/api.ts`
- `frontend/hooks/useActionItems.ts`
- `frontend/components/notulen/ActionItemList.tsx`
- `frontend/app/(main)/meetings/[id]/page.tsx`

---

## 1. Fix Due Date "2099-12-31" (item #2 IMPROVEMENTS.md)

**Masalah:** `dueDate: item.due_date || "2099-12-31"` menampilkan tanggal aneh saat ML tidak detect tenggat waktu.

**Fix:** Ganti ke `?? undefined` supaya komponen tidak render tanggal apapun jika kosong.

```typescript
// page.tsx — sebelum
dueDate: item.due_date || "2099-12-31",

// sesudah
dueDate: item.due_date ?? undefined,
```

`ActionItemList` sudah punya guard `{item.dueDate && (...)}` — jadi kalau `undefined`, kolom tanggal tidak muncul sama sekali.

---

## 2. Priority Berdasarkan Due Date (item #3 IMPROVEMENTS.md — Option B)

**Masalah:** Semua action item hardcoded `"Sedang"`.

**Fix:** Hitung priority dinamis dari `due_date`:

| Kondisi | Priority |
|---------|----------|
| Tidak ada due_date | Rendah |
| Sudah lewat (overdue) | Tinggi |
| ≤ 3 hari lagi | Sedang |
| > 3 hari lagi | Rendah |

```typescript
const getActionItemPriority = (dueDate?: string | null): "Tinggi" | "Sedang" | "Rendah" => {
  if (!dueDate) return "Rendah";
  const diffDays = Math.ceil((new Date(dueDate).getTime() - Date.now()) / 86400000);
  if (diffDays < 0) return "Tinggi";
  if (diffDays <= 3) return "Sedang";
  return "Rendah";
};
```

Tipe `priority` di `ActionItemList` juga diupdate dari `"Tinggi" | "Sedang"` menjadi `"Tinggi" | "Sedang" | "Rendah"`, dengan warna badge baru untuk "Rendah" (slate).

---

## 3. Tambah Action Item Manual (fitur baru)

**Latar belakang:** ML bisa melewatkan tugas yang diucapkan secara implisit. Organizer perlu bisa tambah action item sendiri.

### Perubahan FE

**`api.ts`** — tambah fungsi:
```typescript
export const createActionItem = async (
  meetingId: string,
  data: { task: string; assignee_participant_id?: string | null; due_date?: string | null }
) => {
  const response = await api.post(`/meetings/${meetingId}/action-items`, data);
  return response.data;
};
```

**`hooks/useActionItems.ts`** — tambah hook:
```typescript
export function useCreateActionItem(meetingId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data) => createActionItem(meetingId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["meeting", meetingId] });
    },
  });
}
```

**`ActionItemList.tsx`** — tambah:
- Prop `onAdd?: (data) => void`
- Tombol "Tambah action item manual" (hanya tampil jika `onAdd` ada → organizer only)
- Inline form dengan field: teks tugas (required), assignee dropdown (opsional), due date picker (opsional)
- Form hanya tampil untuk organizer (dicontrol dari `page.tsx` via `isOrganizer ? handleCreateActionItem : undefined`)

**`page.tsx`** — tambah:
- Import `useCreateActionItem`
- Handler `handleCreateActionItem` dengan toast success/error
- Pass `onAdd={isOrganizer ? handleCreateActionItem : undefined}` ke `ActionItemList`

---

## Dependensi BE yang Belum Ada

FE sudah siap memanggil `POST /meetings/{id}/action-items`, tapi **endpoint ini belum ada di backend**. Sampai BE diimplementasikan, tombol tambah manual akan gagal dengan 404/405.

**Yang perlu dibuat di BE (`backend/`):**

| File | Perubahan |
|------|-----------|
| `app/schemas/action_item.py` | Tambah `ActionItemCreateRequest` dengan field `task`, `assignee_participant_id` (opsional), `due_date` (opsional) |
| `app/services/action_item.py` | Tambah `create_action_item(db, meeting_id, user_id, data)` — validasi user adalah organizer |
| `app/routers/action_items.py` | Tambah `POST /meetings/{id}/action-items` route |

**Catatan BE:** Perlu validasi bahwa `assignee_participant_id` adalah peserta yang valid di rapat tersebut (bukan participant dari rapat lain).

---

## Catatan Tambahan: Bug Assign via PATCH

`PATCH /action-items/{id}` di backend saat ini hanya mengupdate `status` — tapi FE mengirim `assignee_id` juga. Backend mengabaikan field ini karena `ActionItemUpdateRequest` schema hanya punya `status`. Fitur assign action item ke peserta belum benar-benar berfungsi end-to-end.

Fix di BE: extend `ActionItemUpdateRequest` dengan `assignee_participant_id: Optional[UUID]` dan tambah logika update di service.

---

## Cara Verifikasi (setelah BE selesai)

1. Buka halaman detail rapat sebagai organizer
2. Scroll ke bagian Action Items
3. Klik "Tambah action item manual"
4. Isi nama tugas, assign ke peserta, set due date
5. Klik Tambah → action item muncul di daftar
6. Verifikasi badge priority muncul sesuai jarak due date
7. Verifikasi action item tanpa due date tidak menampilkan tanggal apapun
