"use client";

import React, { useState, useMemo, useEffect } from "react";
import {
  Square,
  Search,
  Users,
  Video,
  ClipboardList,
  CheckCircle2,
  Clock,
} from "lucide-react";
import { cn, isDateOverdue } from "@/lib/utils";
import { useMyActionItems, useUpdateActionItem } from "@/hooks/useActionItems";
import type { MyActionItem } from "@/types";

type UITaskStatus = "Terlambat" | "Aktif" | "Selesai";

interface UITask {
  id: string;
  task: string;
  meetingTitle: string;
  assignee: string;
  dueDate?: string;
  status: UITaskStatus;
}

export default function ActionItemsPage() {
  const [mounted, setMounted] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [activeFilter, setActiveFilter] = useState<"Semua" | "Aktif" | "Selesai">("Semua");

  useEffect(() => { setMounted(true); }, []);

  const { data, isLoading, isError } = useMyActionItems();
  const { mutate: updateActionItem } = useUpdateActionItem();

  const rawItems: MyActionItem[] = data?.items ?? [];

  // Map API data → format UI
  const tasks: UITask[] = rawItems.map((item) => {
    const isOverdue = !!item.due_date && isDateOverdue(item.due_date);
    const status: UITaskStatus =
      item.status === "done" ? "Selesai" :
      isOverdue ? "Terlambat" : "Aktif";
    return {
      id: item.id,
      task: item.task,
      meetingTitle: item.meeting?.title ?? "–",
      assignee: "Saya",
      dueDate: item.due_date ?? undefined,
      status,
    };
  });

  const handleToggleComplete = (id: string) => {
    const item = tasks.find((t) => t.id === id);
    if (!item) return;
    const newStatus = item.status === "Selesai" ? "open" : "done";
    updateActionItem({ id, status: newStatus });
  };

  const formatDateDisplay = (dateString: string) => {
    if (!mounted) return dateString;
    return new Date(dateString).toLocaleDateString("id-ID", {
      day: "numeric", month: "short", year: "numeric"
    });
  };

  const stats = useMemo(() => ({
    total: tasks.length,
    aktif: tasks.filter((t) => t.status !== "Selesai").length,
    selesai: tasks.filter((t) => t.status === "Selesai").length,
  }), [tasks]);

  const filteredTasks = useMemo(() => {
    const filtered = tasks.filter((task) => {
      const matchesSearch =
        task.task.toLowerCase().includes(searchQuery.toLowerCase()) ||
        task.meetingTitle.toLowerCase().includes(searchQuery.toLowerCase());
      if (activeFilter === "Aktif") return matchesSearch && task.status !== "Selesai";
      if (activeFilter === "Selesai") return matchesSearch && task.status === "Selesai";
      return matchesSearch;
    });
    return filtered.sort((a, b) => {
      const order: Record<UITaskStatus, number> = { Terlambat: 0, Aktif: 1, Selesai: 2 };
      return (order[a.status] ?? 1) - (order[b.status] ?? 1);
    });
  }, [tasks, searchQuery, activeFilter]);

  return (
    <main className="bg-slate-50 min-h-screen text-slate-900 pb-16 pt-8">
      <div className="max-w-7xl mx-auto px-6 space-y-8">

        {/* HERO: judul + ringkasan stat digabung jadi satu panel */}
        <div className="bg-white border border-slate-200 shadow-sm rounded-2xl p-6 md:p-8 flex flex-col lg:flex-row lg:items-center justify-between gap-6 animate-in fade-in-0 slide-in-from-bottom-3 duration-300">
          <div>
            <h1 className="font-display text-2xl font-bold text-slate-900 flex items-center gap-2.5">
              <ClipboardList className="text-indigo-600" size={24} /> Tugas Saya
            </h1>
            <p className="text-slate-500 text-sm mt-1">Semua action item yang di-assign ke kamu dari seluruh rapat.</p>
          </div>

          <div className="flex items-center gap-6 sm:gap-8">
            <div>
              <p className="font-display text-4xl font-bold text-indigo-600">{stats.total}</p>
              <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wide">Total Tugas</span>
            </div>
            <div className="h-10 w-px bg-slate-200 shrink-0" />
            <div className="flex gap-5 sm:gap-6">
              {[
                { label: "Aktif", val: stats.aktif },
                { label: "Selesai", val: stats.selesai },
              ].map((stat, i) => (
                <div key={i}>
                  <p className="font-display text-xl font-bold text-slate-900">{stat.val}</p>
                  <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wide">{stat.label}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Konten */}
        <div className="bg-white border border-slate-200 shadow-sm rounded-2xl p-6 animate-in fade-in-0 slide-in-from-bottom-3 duration-300 delay-150">
          <div className="flex flex-col md:flex-row gap-4 justify-between mb-6">
            <div className="flex bg-slate-50 p-1 rounded-xl border border-slate-200">
              {(["Semua", "Aktif", "Selesai"] as const).map((f) => (
                <button
                  key={f}
                  onClick={() => setActiveFilter(f)}
                  className={cn("px-6 py-2 rounded-lg text-xs font-bold transition",
                    activeFilter === f ? "bg-indigo-600 text-white" : "text-slate-500 hover:text-slate-900"
                  )}
                >
                  {f}
                </button>
              ))}
            </div>
            <div className="relative w-full md:w-80">
              <Search className="absolute left-3.5 top-3 text-slate-400" size={16} />
              <input
                className="w-full bg-white border border-slate-300 rounded-xl py-2.5 pl-10 pr-4 outline-none text-sm text-slate-900 placeholder-slate-400 focus:border-indigo-400 focus:ring-2 focus:ring-indigo-400/20 transition"
                placeholder="Cari tugas..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
          </div>

          <div className="space-y-3">
            {isLoading ? (
              [...Array(3)].map((_, i) => (
                <div key={i} className="h-16 rounded-xl bg-slate-100 animate-pulse" />
              ))
            ) : isError ? (
              <p className="text-center text-rose-400 py-10 text-sm">Gagal memuat tugas. Pastikan backend sudah berjalan.</p>
            ) : filteredTasks.length > 0 ? (
              filteredTasks.map((item) => (
                <div
                  key={item.id}
                  className={cn(
                    "border border-slate-200 p-4 rounded-xl flex items-start gap-4 transition",
                    item.status === "Selesai" ? "bg-slate-50 opacity-50" : "hover:border-slate-300"
                  )}
                >
                  <button
                    type="button"
                    onClick={() => handleToggleComplete(item.id)}
                    className="shrink-0 mt-0.5 cursor-pointer"
                    title={item.status === "Selesai" ? "Tandai belum selesai" : "Tandai selesai"}
                  >
                    {item.status === "Selesai" ? (
                      <CheckCircle2 className="text-emerald-400" size={20} />
                    ) : (
                      <Square
                        className={cn(
                          "transition",
                          item.status === "Terlambat" ? "text-rose-400/40 hover:text-rose-500" : "text-indigo-600/40 hover:text-indigo-600"
                        )}
                        size={20}
                      />
                    )}
                  </button>
                  <div className="flex-1 min-w-0">
                    <p className={cn("text-sm font-semibold text-slate-900 truncate", item.status === "Selesai" && "line-through text-slate-500")}>
                      {item.task}
                    </p>
                    <div className="flex flex-wrap gap-3 mt-2 text-[11px] text-slate-500 items-center">
                      <span className="flex items-center gap-1"><Users size={12} /> {item.assignee}</span>
                      {item.dueDate && (
                        <span className="flex items-center gap-1"><Clock size={12} /> {formatDateDisplay(item.dueDate)}</span>
                      )}
                      <span className="flex items-center gap-1 bg-indigo-50 px-2 py-0.5 rounded text-indigo-600 font-medium">
                        <Video size={11} /> {item.meetingTitle}
                      </span>
                      <span className={cn(
                        "px-2 py-0.5 rounded font-bold border text-[10px]",
                        item.status === "Terlambat" && "bg-rose-50 text-rose-600 border-rose-200",
                        item.status === "Aktif" && "bg-indigo-50 text-indigo-700 border-indigo-200",
                        item.status === "Selesai" && "bg-emerald-50 text-emerald-700 border-emerald-200"
                      )}>
                        {item.status}
                      </span>
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-center text-slate-500 py-10 text-sm italic">Tidak ada tugas ditemukan.</p>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
