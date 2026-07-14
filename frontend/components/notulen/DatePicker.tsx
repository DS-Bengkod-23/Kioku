"use client";

import React, { useEffect, useRef, useState } from "react";
import { ChevronLeft, ChevronRight, Clock } from "lucide-react";
import { cn } from "@/lib/utils";

interface DatePickerProps {
  value: string | null;
  onChange: (date: string | null) => void;
  variant?: "badge" | "field";
  placeholder?: string;
  className?: string;
  /** Kalau true, value/onChange pakai format "YYYY-MM-DDTHH:mm" dan panel menampilkan pemilih jam. */
  withTime?: boolean;
  /** Kalau false, sembunyikan tombol "Hapus" (dipakai untuk field wajib seperti jadwal rapat). */
  allowClear?: boolean;
  /** Kalau true, wrapper ikut melebar penuh (dipakai saat trigger perlu w-full, mis. di form). */
  fullWidth?: boolean;
}

const WEEKDAY_LABELS = ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"];
const HOURS = Array.from({ length: 24 }, (_, i) => String(i).padStart(2, "0"));
const MINUTES = ["00", "05", "10", "15", "20", "25", "30", "35", "40", "45", "50", "55"];
const DEFAULT_TIME = "09:00";

function toDateString(d: Date): string {
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function parseDateString(s: string): Date {
  const [year, month, day] = s.split("-").map(Number);
  return new Date(year, month - 1, day);
}

function splitDateTime(value: string | null): { datePart: string | null; timePart: string } {
  if (!value) return { datePart: null, timePart: DEFAULT_TIME };
  const [datePart, timePart] = value.split("T");
  return { datePart: datePart || null, timePart: timePart ? timePart.slice(0, 5) : DEFAULT_TIME };
}

export function formatShortDate(dateStr?: string | null): string {
  if (!dateStr) return "";
  return parseDateString(dateStr).toLocaleDateString("id-ID", { day: "numeric", month: "short" });
}

function formatFullDate(dateStr: string): string {
  return parseDateString(dateStr).toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" });
}

export default function DatePicker({
  value,
  onChange,
  variant = "badge",
  placeholder,
  className,
  withTime = false,
  allowClear = true,
  fullWidth = false,
}: DatePickerProps) {
  const [open, setOpen] = useState(false);
  const { datePart, timePart } = splitDateTime(value);
  const selected = datePart ? parseDateString(datePart) : null;
  const [viewMonth, setViewMonth] = useState(() => selected ?? new Date());
  const [timeValue, setTimeValue] = useState(timePart);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setTimeValue(timePart);
  }, [timePart]);

  useEffect(() => {
    if (!open) return;
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [open]);

  const handleToggleOpen = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!open) setViewMonth(selected ?? new Date());
    setOpen((v) => !v);
  };

  const emit = (nextDatePart: string, nextTime: string) => {
    onChange(withTime ? `${nextDatePart}T${nextTime}` : nextDatePart);
  };

  const handlePick = (day: Date) => {
    const nextDatePart = toDateString(day);
    emit(nextDatePart, timeValue);
    if (!withTime) setOpen(false);
  };

  const handleTimeChange = (part: "hour" | "minute", val: string) => {
    const [h, m] = timeValue.split(":");
    const next = part === "hour" ? `${val}:${m}` : `${h}:${val}`;
    setTimeValue(next);
    if (datePart) emit(datePart, next);
  };

  const handleClear = (e: React.MouseEvent) => {
    e.stopPropagation();
    onChange(null);
    setOpen(false);
  };

  const handleToday = (e: React.MouseEvent) => {
    e.stopPropagation();
    handlePick(new Date());
  };

  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const year = viewMonth.getFullYear();
  const month = viewMonth.getMonth();
  const firstOfMonth = new Date(year, month, 1);
  const startOffset = (firstOfMonth.getDay() + 6) % 7; // Monday-first
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const cells: (Date | null)[] = [
    ...Array(startOffset).fill(null),
    ...Array.from({ length: daysInMonth }, (_, i) => new Date(year, month, i + 1)),
  ];

  const monthLabel = viewMonth.toLocaleDateString("id-ID", { month: "long", year: "numeric" });

  const triggerLabel = datePart
    ? withTime
      ? `${formatFullDate(datePart)}, ${timePart}`
      : formatShortDate(datePart)
    : (placeholder ?? (variant === "badge" ? "+ Deadline" : withTime ? "Pilih tanggal & waktu" : "Pilih tanggal"));

  return (
    <span
      className={cn("relative", fullWidth ? "flex w-full" : "inline-flex")}
      ref={containerRef}
      onClick={(e) => e.stopPropagation()}
    >
      {variant === "badge" ? (
        <button
          type="button"
          onClick={handleToggleOpen}
          className={cn(
            "flex items-center gap-1.5 text-sm transition",
            value ? "text-slate-500 hover:text-indigo-600" : "text-slate-400 hover:text-indigo-600",
            className
          )}
          title={value ? "Ubah deadline" : "Tambah deadline"}
        >
          <Clock size={15} />
          {triggerLabel}
        </button>
      ) : (
        <button
          type="button"
          onClick={handleToggleOpen}
          className={cn(
            "text-xs px-3 py-2 rounded-lg border border-slate-200 bg-white hover:border-indigo-300 focus:outline-none focus:border-indigo-400 text-left",
            datePart ? "text-slate-700" : "text-slate-400",
            className
          )}
        >
          {triggerLabel}
        </button>
      )}

      {open && (
        <div className="absolute top-full left-0 mt-1 z-50 w-60 rounded-xl border border-slate-200 bg-white shadow-lg p-3">
          <div className="flex items-center justify-between mb-2">
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); setViewMonth(new Date(year, month - 1, 1)); }}
              className="p-1 rounded hover:bg-slate-100 text-slate-500"
            >
              <ChevronLeft size={14} />
            </button>
            <span className="text-xs font-semibold text-slate-700 capitalize">{monthLabel}</span>
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); setViewMonth(new Date(year, month + 1, 1)); }}
              className="p-1 rounded hover:bg-slate-100 text-slate-500"
            >
              <ChevronRight size={14} />
            </button>
          </div>

          <div className="grid grid-cols-7 gap-0.5 mb-1">
            {WEEKDAY_LABELS.map((w) => (
              <span key={w} className="text-[9px] font-semibold text-slate-400 text-center py-1">
                {w}
              </span>
            ))}
          </div>

          <div className="grid grid-cols-7 gap-0.5">
            {cells.map((day, i) => {
              if (!day) return <span key={`empty-${i}`} />;
              const isSelected = selected && toDateString(day) === toDateString(selected);
              const isToday = toDateString(day) === toDateString(today);
              return (
                <button
                  key={toDateString(day)}
                  type="button"
                  onClick={(e) => { e.stopPropagation(); handlePick(day); }}
                  className={cn(
                    "text-[10px] rounded-md py-1 transition",
                    isSelected
                      ? "bg-indigo-600 text-white font-semibold"
                      : isToday
                        ? "bg-indigo-50 text-indigo-600 font-semibold"
                        : "text-slate-600 hover:bg-slate-100"
                  )}
                >
                  {day.getDate()}
                </button>
              );
            })}
          </div>

          {withTime && (
            <div className="flex items-center gap-1.5 mt-2 pt-2 border-t border-slate-100" onClick={(e) => e.stopPropagation()}>
              <Clock size={12} className="text-slate-400 shrink-0" />
              <select
                value={timeValue.split(":")[0]}
                onChange={(e) => handleTimeChange("hour", e.target.value)}
                className="flex-1 text-[11px] px-1.5 py-1 rounded border border-slate-200 bg-white focus:outline-none focus:border-indigo-400"
              >
                {HOURS.map((h) => (
                  <option key={h} value={h}>{h}</option>
                ))}
              </select>
              <span className="text-slate-400 text-[11px]">:</span>
              <select
                value={timeValue.split(":")[1]}
                onChange={(e) => handleTimeChange("minute", e.target.value)}
                className="flex-1 text-[11px] px-1.5 py-1 rounded border border-slate-200 bg-white focus:outline-none focus:border-indigo-400"
              >
                {MINUTES.map((m) => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
            </div>
          )}

          <div className="flex items-center justify-between mt-2 pt-2 border-t border-slate-100">
            <button
              type="button"
              onClick={handleToday}
              className="text-[10px] text-indigo-600 hover:text-indigo-700 font-medium"
            >
              Hari ini
            </button>
            {withTime ? (
              <button
                type="button"
                onClick={(e) => { e.stopPropagation(); setOpen(false); }}
                disabled={!datePart}
                className="text-[10px] text-indigo-600 hover:text-indigo-700 font-medium disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Selesai
              </button>
            ) : allowClear && value ? (
              <button
                type="button"
                onClick={handleClear}
                className="text-[10px] text-slate-400 hover:text-rose-600 font-medium"
              >
                Hapus deadline
              </button>
            ) : null}
          </div>
        </div>
      )}
    </span>
  );
}
