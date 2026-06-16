# MeetMate Frontend

Next.js frontend untuk MeetMate.

**Owner:** Helena

---

## Stack

- **Next.js 14** (App Router)
- **shadcn/ui** - komponen UI
- **Tailwind CSS** - styling
- **React Query** - data fetching + caching

---

## Struktur Folder

```
frontend/
├── app/
│   ├── layout.tsx
│   ├── page.tsx                  # halaman utama (redirect ke /meetings)
│   ├── globals.css
│   ├── favicon.ico
│   ├── fonts/
│   │   ├── GeistVF.woff
│   │   └── GeistMonoVF.woff
│   ├── (auth)/                   # route group auth (no layout utama)
│   │   ├── login/
│   │   │   └── page.tsx
│   │   ├── register/
│   │   │   └── page.tsx
│   │   └── forgot-password/
│   │       └── page.tsx
│   ├── (main)/                   # route group dengan layout sidebar
│   │   ├── layout.tsx            # layout utama (navbar)
│   │   ├── meetings/
│   │   │   ├── page.tsx          # dashboard list meetings
│   │   │   ├── new/
│   │   │   │   └── page.tsx      # form create meeting
│   │   │   └── [id]/
│   │   │       ├── page.tsx      # detail meeting + notulen
│   │   │       ├── edit/
│   │   │       │   └── page.tsx  # edit meeting
│   │   │       └── recording/
│   │   │           └── page.tsx  # upload & proses rekaman
│   │   ├── action-items/
│   │   │   └── page.tsx          # semua action item milik user
│   │   └── profile/
│   │       └── page.tsx          # profil & pengaturan akun
│   └── check-in/
│       └── [token]/
│           └── page.tsx          # halaman publik check-in (no login)
├── components/
│   ├── ui/                       # shadcn components (auto-generated)
│   │   ├── alert-dialog.tsx
│   │   ├── button.tsx
│   │   ├── dropdown-menu.tsx
│   │   └── form-error.tsx
│   ├── meetings/
│   │   ├── MeetingCard.tsx
│   │   ├── MeetingForm.tsx
│   │   ├── ParticipantList.tsx
│   │   └── AttendanceTable.tsx
│   ├── recording/
│   │   ├── UploadZone.tsx
│   │   └── ProcessingStatus.tsx
│   └── notulen/
│       ├── TranscriptView.tsx
│       ├── SummaryCard.tsx
│       └── ActionItemList.tsx
├── lib/
│   ├── api.ts                    # axios/fetch wrapper
│   └── utils.ts
├── hooks/
│   ├── useMeetings.ts
│   ├── useMeeting.ts
│   ├── useActionItems.ts
│   └── useRecording.ts          # polling status processing rekaman
├── types/
│   └── index.ts                  # TypeScript types sesuai API Contract
├── package.json
├── tailwind.config.ts
├── tsconfig.json
└── README.md
```

---

## Setup

**1. Install dependency**
```bash
npm install
```

**2. Pastikan backend jalan di** `http://localhost:8000`

**3. Jalankan dev server**
```bash
npm run dev
```

Buka http://localhost:3000

---

## Daftar Halaman

| Halaman | Route | Auth |
|---|---|---|
| Login | /login | No |
| Register | /register | No |
| Dashboard meetings | /meetings | Yes |
| Create meeting | /meetings/new | Yes |
| Detail meeting | /meetings/[id] | Yes |
| Edit meeting | /meetings/[id]/edit | Yes |
| Upload rekaman | /meetings/[id]/recording | Yes |
| Check-in peserta | /check-in/[token] | No (public) |
| Action items saya | /action-items | Yes |

---

## Environment Variables

Buat file `.env.local` di folder ini:
```
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

---

## Panduan Komponen

Semua komponen UI pakai shadcn/ui. Install komponen baru dengan:
```bash
npx shadcn-ui@latest add <nama-komponen>
```

Lihat https://ui.shadcn.com untuk katalog komponen.