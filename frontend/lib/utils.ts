import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function isDateOverdue(dueDate: string): boolean {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  // Re-anchor ke local midnight (sama seperti daysUntil() di bawah) — tanggal-only
  // string ("2026-07-16") di-parse sebagai UTC midnight oleh spec ECMAScript, jadi
  // tanpa ini, task yang due "hari ini" bisa salah dianggap overdue di timezone
  // dengan offset negatif terhadap UTC.
  const due = new Date(dueDate);
  due.setHours(0, 0, 0, 0);
  return due < today;
}

// Jumlah hari kalender (bisa negatif kalau sudah lewat) sampai dueDate, dihitung
// dari local midnight ke local midnight — supaya konsisten dengan isDateOverdue()
// dan tidak sensitif terhadap jam-saat-ini/timezone seperti perhitungan mentah
// `(new Date(dueDate) - Date.now()) / 86400000`.
export function daysUntil(dueDate: string): number {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const due = new Date(dueDate);
  due.setHours(0, 0, 0, 0);
  return Math.round((due.getTime() - today.getTime()) / 86400000);
}

// localStorage bisa berisi JSON korup (mis. literal string "undefined" dari
// JSON.stringify(undefined)) — parse selalu lewat helper ini supaya tidak ada
// JSON.parse mentah yang bisa meng-crash render.
export function readUserProfile(): { email?: string; name?: string; [key: string]: unknown } {
  if (typeof window === "undefined") return {};
  const raw = localStorage.getItem("user_profile");
  if (!raw) return {};
  try {
    return JSON.parse(raw);
  } catch {
    localStorage.removeItem("user_profile");
    return {};
  }
}

export function extractApiError(err: unknown, fallback: string): string {
  const detail = (err as any)?.response?.data?.detail;
  if (!detail) return fallback;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((e: any) => e.msg ?? String(e)).join(" · ");
  }
  return fallback;
}
