# Root Cause: Logged-in User Bisa Akses Halaman /login

## Context

User melaporkan bahwa setelah login, mereka masih bisa navigasi ke halaman `/login` tanpa di-redirect ke halaman utama. Ini seharusnya tidak terjadi — kalau sudah punya token valid, akses ke `/login` harus redirect ke `/meetings`.

---

## Root Cause

**File:** `frontend/middleware.ts`, baris 4–17

```typescript
const PUBLIC_PATHS = ["/", "/login", "/register", "/forgot-password"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Halaman publik — boleh tanpa login
  if (PUBLIC_PATHS.includes(pathname)) {
    return NextResponse.next();  // ← MASALAH ADA DI SINI
  }

  // ...baru cek token di bawah...
  const token = request.cookies.get("access_token")?.value;
  if (!token) { redirect ke /login }
```

Middleware hanya punya **dua jalur**:
1. Path publik → langsung lolos (`NextResponse.next()`), tanpa cek token sama sekali
2. Path private tanpa token → redirect ke `/login`

**Jalur yang hilang:**
- Path publik (login/register) + punya token → **seharusnya redirect ke `/meetings`, tapi tidak ada logika ini**

Jadi ketika user sudah login (cookie `access_token` ada), lalu buka `/login`, middleware langsung loloskan karena `/login` ada di `PUBLIC_PATHS` — tanpa pernah melihat token-nya.

---

## Kenapa Tidak Tertangkap di Client-Side?

`frontend/app/(auth)/login/page.tsx` adalah client component yang tidak punya `useEffect` untuk cek localStorage/cookie saat halaman mount. Tidak ada auth context/hook yang bisa mendeteksi "sudah login" dan redirect otomatis.

Token disimpan di dua tempat:
- `localStorage` → untuk API calls (dibaca client-side)
- Cookie `access_token` → untuk middleware (dibaca server-side)

Middleware **bisa** baca cookie, tapi tidak memanfaatkannya untuk auth pages.

---

## Fix yang Diperlukan

### 1. `frontend/middleware.ts` (perubahan utama)
Tambahkan cek: jika request ke `/login` atau `/register` dan cookie `access_token` ada → redirect ke `/meetings`.

```typescript
// Sebelum cek PUBLIC_PATHS, tambahkan:
const AUTH_ONLY_PATHS = ["/login", "/register", "/forgot-password"];
const token = request.cookies.get("access_token")?.value;

if (AUTH_ONLY_PATHS.includes(pathname) && token) {
  return NextResponse.redirect(new URL("/meetings", request.url));
}
```

### 2. (Opsional) `frontend/app/(auth)/login/page.tsx`
Tambahkan `useEffect` sebagai fallback client-side guard:
```typescript
useEffect(() => {
  if (localStorage.getItem("access_token")) {
    router.replace("/meetings");
  }
}, []);
```

---

## Verification

1. Login → buka tab baru → manual navigate ke `/login` → harus redirect ke `/meetings`
2. Belum login → buka `/login` → harus tampil form login seperti biasa
3. Logout → buka `/login` → harus tampil form login (token sudah dihapus)
