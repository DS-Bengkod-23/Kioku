import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function isDateOverdue(dueDate: string): boolean {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return new Date(dueDate) < today;
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

export function extractApiError(err: unknown, fallback: string): string {
  const detail = (err as any)?.response?.data?.detail;
  if (!detail) return fallback;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((e: any) => e.msg ?? String(e)).join(" · ");
  }
  return fallback;
}
