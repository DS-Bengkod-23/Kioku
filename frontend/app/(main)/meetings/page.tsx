"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { Search, Filter, Plus, ChevronDown, ChevronLeft, ChevronRight } from "lucide-react";
import MeetingCard from "@/components/meetings/MeetingCard";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useMeetings, useSearchMeetings } from "@/hooks/useMeetings";
import type { MeetingsParams } from "@/lib/api";
import type { MeetingListItem } from "@/types";

const STATUS_MAP: Record<string, "Dijadwalkan" | "Selesai" | "Dibatalkan"> = {
  scheduled: "Dijadwalkan",
  completed: "Selesai",
  cancelled: "Dibatalkan",
};

const LIMIT = 9;

function formatDate(isoString: string) {
  return new Date(isoString).toLocaleDateString("id-ID", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function MeetingsDashboard() {
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("Semua Status");
  const [userName, setUserName] = useState("Pengguna");
  const [page, setPage] = useState(1);

  // Debounce search 300ms
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(searchQuery);
      setPage(1); // reset ke halaman 1 saat search berubah
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Reset halaman saat filter status berubah
  useEffect(() => { setPage(1); }, [statusFilter]);

  // Ambil nama dari localStorage untuk sapaan
  useEffect(() => {
    const profile = JSON.parse(localStorage.getItem("user_profile") || "{}");
    if (profile.name) setUserName(profile.name.split(" ")[0]);
  }, []);

  const apiStatus = statusFilter === "Semua Status" ? undefined : (
    statusFilter === "Dijadwalkan" ? "scheduled" :
    statusFilter === "Selesai" ? "completed" : "cancelled"
  ) as MeetingsParams["status"];

  const { data: meetingsData, isLoading, isError } = useMeetings(
    debouncedQuery ? undefined : { status: apiStatus, page, limit: LIMIT }
  );
  const { data: searchData, isLoading: isSearching } = useSearchMeetings(debouncedQuery);

  const rawItems: MeetingListItem[] = debouncedQuery
    ? (searchData?.items ?? [])
    : (meetingsData?.items ?? []);

  const total = debouncedQuery ? (searchData?.total ?? 0) : (meetingsData?.total ?? 0);
  const totalPages = Math.ceil(total / LIMIT);

  const meetings = rawItems.map((m) => ({
    id: m.id,
    title: m.title,
    status: STATUS_MAP[m.status] ?? "Dijadwalkan",
    date: formatDate(m.scheduled_at),
    location: m.location ?? "–",
    totalParticipants: m.participant_count ?? 0,
    attendedParticipants: m.attendance_count ?? 0,
    hasTranscript: m.processing_status === "completed",
    hasRecording: m.has_recording ?? false,
  }));

  const loading = isLoading || isSearching;

  return (
    <div className="w-full min-h-screen bg-slate-50 text-slate-900 font-sans pb-16">
      <main className="max-w-7xl mx-auto px-6 pt-8 space-y-8">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Halo, {userName}! 👋</h1>
          <p className="text-slate-500 text-sm mt-1">Kelola dan tinjau rapat pintar kamu dari sini.</p>
        </div>

        {/* UTILITY BAR */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 animate-in fade-in-0 slide-in-from-bottom-2 duration-300">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
            <input
              type="text"
              placeholder="Cari rapat..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-white border border-slate-200 text-slate-900 text-sm placeholder-slate-400 focus:outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-400/20 transition-all shadow-sm"
            />
          </div>

          <div className="flex items-center gap-2">
            <DropdownMenu>
              <DropdownMenuTrigger className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-white border border-slate-200 text-sm font-medium text-slate-600 hover:border-slate-300 transition-all outline-none shadow-sm">
                <Filter size={14} className="text-indigo-500" />
                <span>{statusFilter}</span>
                <ChevronDown size={13} className="opacity-50" />
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="bg-white border border-slate-200 text-slate-700 rounded-xl shadow-lg p-1 min-w-[160px]">
                {["Semua Status", "Dijadwalkan", "Selesai", "Dibatalkan"].map((status) => (
                  <DropdownMenuItem
                    key={status}
                    onClick={() => setStatusFilter(status)}
                    className="rounded-lg px-3 py-2 text-sm focus:bg-indigo-600 focus:text-white cursor-pointer transition-colors"
                  >
                    {status}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>

            <Link
              href="/meetings/new"
              className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl bg-gradient-to-r from-indigo-500 to-violet-600 hover:from-indigo-400 hover:to-violet-500 text-sm font-semibold text-white shadow-md shadow-indigo-500/25 transition-all duration-300"
            >
              <Plus size={15} />
              Buat Rapat
            </Link>
          </div>
        </div>

        {/* LIST CARDS */}
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="h-44 rounded-2xl bg-slate-200/70 animate-pulse" />
            ))}
          </div>
        ) : isError ? (
          <div className="text-center py-20 bg-white border border-dashed border-rose-200 rounded-2xl">
            <p className="text-rose-400 text-sm">Gagal memuat data rapat. Pastikan backend sudah berjalan.</p>
          </div>
        ) : meetings.length > 0 ? (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 animate-in fade-in-0 duration-300">
              {meetings.map((meeting) => (
                <MeetingCard key={meeting.id} {...meeting} />
              ))}
            </div>

            {!debouncedQuery && totalPages > 1 && (
              <div className="flex items-center justify-center gap-2 pt-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="p-2 rounded-xl bg-white border border-slate-200 text-slate-500 hover:text-slate-900 disabled:opacity-30 disabled:cursor-not-allowed transition shadow-sm"
                >
                  <ChevronLeft size={15} />
                </button>
                <div className="flex items-center gap-1">
                  {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
                    <button
                      key={p}
                      onClick={() => setPage(p)}
                      className={`w-8 h-8 rounded-lg text-xs font-bold transition ${
                        p === page
                          ? "bg-indigo-600 text-white shadow-md shadow-indigo-500/20"
                          : "text-slate-500 hover:text-slate-900 hover:bg-slate-100"
                      }`}
                    >
                      {p}
                    </button>
                  ))}
                </div>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="p-2 rounded-xl bg-white border border-slate-200 text-slate-500 hover:text-slate-900 disabled:opacity-30 disabled:cursor-not-allowed transition shadow-sm"
                >
                  <ChevronRight size={15} />
                </button>
                <span className="text-xs text-slate-400 ml-1">{total} rapat</span>
              </div>
            )}
          </>
        ) : (
          <div className="text-center py-24 bg-white border border-dashed border-slate-200 rounded-2xl">
            <div className="text-4xl mb-4">📋</div>
            <p className="text-slate-700 font-semibold mb-1">
              {debouncedQuery ? "Rapat tidak ditemukan" : "Belum ada rapat"}
            </p>
            <p className="text-slate-400 text-sm mb-6">
              {debouncedQuery ? `Tidak ada hasil untuk "${debouncedQuery}"` : "Buat rapat pertama kamu dan mulai catat notulen otomatis."}
            </p>
            {!debouncedQuery && (
              <Link
                href="/meetings/new"
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold transition"
              >
                <Plus size={15} /> Buat Rapat Pertama
              </Link>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
