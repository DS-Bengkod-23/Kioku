import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const PUBLIC_PATHS = ["/", "/login", "/register", "/forgot-password"];
const AUTH_ONLY_PATHS = ["/", "/login", "/register", "/forgot-password"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Skip auth di development
  if (process.env.NODE_ENV === "development" && process.env.NEXT_PUBLIC_SKIP_AUTH === "true") {
    return NextResponse.next();
  }

  const token = request.cookies.get("access_token")?.value;

  // Kalau sudah login, jangan bisa balik ke halaman auth
  if (AUTH_ONLY_PATHS.includes(pathname) && token) {
    return NextResponse.redirect(new URL("/meetings", request.url));
  }

  // Halaman publik — boleh tanpa login
  if (PUBLIC_PATHS.includes(pathname)) {
    return NextResponse.next();
  }

  // Halaman check-in publik (magic link, no auth)
  if (pathname.startsWith("/check-in")) {
    return NextResponse.next();
  }

  if (!token) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("redirect", pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  // Jalankan middleware di semua path kecuali aset statis
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
