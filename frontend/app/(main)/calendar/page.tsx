"use client";

import React, { useState, useMemo } from "react";
import Link from "next/link";
import { ChevronLeft, ChevronRight, Calendar as CalendarIcon, Clock, MapPin } from "lucide-react";
import { cn } from "@/lib/utils";
import { useMeetings } from "@/hooks/useMeetings";
import type { MeetingListItem, MeetingStatus } from "@/types";

const STATUS_DOT: Record<MeetingStatus, string> = {
  scheduled: "bg-indigo-500",
  completed: "bg-emerald-600",
  cancelled: "bg-red-400",
};

function dateKey(d: Date) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function isSameDay(a: Date, b: Date) {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
}

export default function CalendarPage() {
  const [currentMonth, setCurrentMonth] = useState(() => {
    const d = new Date();
    return new Date(d.getFullYear(), d.getMonth(), 1);
  });
  const [selectedDate, setSelectedDate] = useState(() => new Date());

  // Ambil meeting user dalam 1 request (limit dibatasi 100 oleh backend,
  // le=100 di routers/meetings.py), lalu dikelompokkan per tanggal di client.
  // Cukup untuk skala tim kecil-menengah; kalau >100 meeting dibutuhkan
  // sekaligus, backend perlu filter date_from/date_to (lihat Bug 7).
  const { data, isLoading, isError } = useMeetings({ limit: 100 });
  const meetings: MeetingListItem[] = data?.items ?? [];

  const meetingsByDate = useMemo(() => {
    const map = new Map<string, MeetingListItem[]>();
    for (const m of meetings) {
      const key = dateKey(new Date(m.scheduled_at));
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(m);
    }
    return map;
  }, [meetings]);

  const monthLabel = currentMonth.toLocaleDateString("id-ID", { month: "long", year: "numeric" });

  const dayHeaders = useMemo(() => {
    const ref = new Date(2024, 0, 7); // Minggu
    return Array.from({ length: 7 }, (_, i) => {
      const d = new Date(ref);
      d.setDate(ref.getDate() + i);
      return d.toLocaleDateString("id-ID", { weekday: "short" });
    });
  }, []);

  const gridDays = useMemo(() => {
    const startOffset = currentMonth.getDay(); // 0 = Minggu
    const gridStart = new Date(currentMonth);
    gridStart.setDate(currentMonth.getDate() - startOffset);

    const daysInMonth = new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1, 0).getDate();
    const totalCellsNeeded = startOffset + daysInMonth;
    const rows = Math.ceil(totalCellsNeeded / 7);
    const totalCells = rows * 7;

    return Array.from({ length: totalCells }, (_, i) => {
      const d = new Date(gridStart);
      d.setDate(gridStart.getDate() + i);
      return d;
    });
  }, [currentMonth]);

  const today = new Date();
  const selectedMeetings = meetingsByDate.get(dateKey(selectedDate)) ?? [];

  const handlePrevMonth = () => setCurrentMonth((m) => new Date(m.getFullYear(), m.getMonth() - 1, 1));
  const handleNextMonth = () => setCurrentMonth((m) => new Date(m.getFullYear(), m.getMonth() + 1, 1));

  return (
    <div className="w-full min-h-screen bg-slate-50 text-slate-900 font-sans pb-16">
      <main className="max-w-7xl mx-auto px-6 pt-8 space-y-8">
        {/* HERO */}
        <div className="bg-white border border-slate-200 shadow-sm rounded-2xl p-6 md:p-8 flex flex-col lg:flex-row lg:items-center justify-between gap-6 animate-in fade-in-0 slide-in-from-bottom-3 duration-300">
          <div>
            <h1 className="font-display text-2xl font-bold text-slate-900 flex items-center gap-2.5">
              <CalendarIcon className="text-indigo-600" size={24} /> Kalender Rapat
            </h1>
            <p className="text-slate-500 text-sm mt-1">Lihat jadwal rapat kamu dalam tampilan bulanan.</p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handlePrevMonth}
              className="p-2 rounded-xl bg-white border border-slate-200 text-slate-500 hover:text-slate-900 transition shadow-sm"
            >
              <ChevronLeft size={16} />
            </button>
            <span className="font-display text-sm font-bold text-slate-900 w-32 text-center capitalize">{monthLabel}</span>
            <button
              onClick={handleNextMonth}
              className="p-2 rounded-xl bg-white border border-slate-200 text-slate-500 hover:text-slate-900 transition shadow-sm"
            >
              <ChevronRight size={16} />
            </button>
          </div>
        </div>

        {/* GRID + SELECTED DAY LIST */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 animate-in fade-in-0 slide-in-from-bottom-2 duration-300">
          {/* CALENDAR GRID */}
          <div className="lg:col-span-2 bg-white border border-slate-200 shadow-sm rounded-2xl p-4">
            <div className="grid grid-cols-7 gap-1 mb-1">
              {dayHeaders.map((label) => (
                <div key={label} className="text-center text-[10px] font-bold text-slate-400 uppercase py-1.5">
                  {label}
                </div>
              ))}
            </div>
            <div className="grid grid-cols-7 gap-1">
              {gridDays.map((d, i) => {
                const inMonth = d.getMonth() === currentMonth.getMonth();
                const isToday = isSameDay(d, today);
                const isSelected = isSameDay(d, selectedDate);
                const dayMeetings = meetingsByDate.get(dateKey(d)) ?? [];

                return (
                  <button
                    key={i}
                    onClick={() => setSelectedDate(d)}
                    className={cn(
                      "h-11 rounded-lg flex flex-col items-center justify-center gap-0.5 text-[11px] font-semibold transition",
                      !inMonth && "text-slate-300",
                      inMonth && !isSelected && "text-slate-700 hover:bg-slate-50",
                      isSelected && "bg-indigo-600 text-white",
                      isToday && !isSelected && "ring-1 ring-indigo-400 text-indigo-700"
                    )}
                  >
                    <span>{d.getDate()}</span>
                    {dayMeetings.length > 0 && (
                      <div className="flex items-center gap-0.5">
                        {dayMeetings.slice(0, 3).map((m, idx) => (
                          <span
                            key={idx}
                            className={cn(
                              "h-1 w-1 rounded-full",
                              isSelected ? "bg-white" : STATUS_DOT[m.status]
                            )}
                          />
                        ))}
                      </div>
                    )}
                  </button>
                );
              })}
            </div>
          </div>

          {/* SELECTED DAY MEETING LIST */}
          <div className="bg-white border border-slate-200 shadow-sm rounded-2xl p-4">
            <h2 className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-3">
              {selectedDate.toLocaleDateString("id-ID", { weekday: "long", day: "numeric", month: "long", year: "numeric" })}
            </h2>

            {isLoading ? (
              <div className="space-y-2">
                {[...Array(2)].map((_, i) => (
                  <div key={i} className="h-14 rounded-xl bg-slate-100 animate-pulse" />
                ))}
              </div>
            ) : isError ? (
              <p className="text-rose-400 text-xs">Gagal memuat data rapat.</p>
            ) : selectedMeetings.length > 0 ? (
              <div className="space-y-2">
                {selectedMeetings.map((m) => (
                  <Link
                    key={m.id}
                    href={`/meetings/${m.id}`}
                    className="block border border-slate-200 rounded-xl p-2.5 hover:border-indigo-300 hover:bg-indigo-50/30 transition"
                  >
                    <p className="text-sm font-bold text-slate-900 line-clamp-1">{m.title}</p>
                    <div className="flex items-center gap-3 mt-1.5 text-[11px] text-slate-500">
                      <span className="flex items-center gap-1">
                        <Clock size={11} />
                        {new Date(m.scheduled_at).toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" })}
                      </span>
                      {m.location && (
                        <span className="flex items-center gap-1 line-clamp-1">
                          <MapPin size={11} /> {m.location}
                        </span>
                      )}
                    </div>
                  </Link>
                ))}
              </div>
            ) : (
              <p className="text-slate-400 text-xs italic py-6 text-center">Tidak ada rapat di tanggal ini.</p>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
