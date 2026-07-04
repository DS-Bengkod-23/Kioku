"use client";

import React, { useState, useMemo, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  Square,
  Search,
  Users,
  Video,
  ClipboardList,
  AlertCircle,
  CheckCircle2,
  Clock,
  ArrowLeft
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
  const router = useRouter();
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
      <div className="max-w-5xl mx-auto px-6 space-y-8">

        <button
          onClick={() => router.back()}
          className="inline-flex items-center gap-2 text-slate-500 hover:text-slate-900 transition text-xs font-medium mb-4"
        >
          <ArrowLeft size={16} />
          Kembali ke Dashboard
        </button>

        <div className="space-y-1">
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2.5">
            <ClipboardList className="text-blue-700" size={26} /> Tugas Saya
          </h1>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5 animate-in fade-in-0 slide-in-from-bottom-3 duration-300 delay-75">
          {[
            { label: "Total Tugas", val: stats.total, icon: ClipboardList, style: "bg-blue-50 border-blue-200 text-blue-700" },
            { label: "Tugas Aktif", val: stats.aktif, icon: AlertCircle, style: "bg-amber-50 border-amber-200 text-amber-700" },
            { label: "Tugas Selesai", val: stats.selesai, icon: CheckCircle2, style: "bg-emerald-50 border-emerald-200 text-emerald-700" },
          ].map((stat, i) => (
            <div key={i} className="bg-white border border-slate-200 shadow-sm rounded-2xl p-5 flex items-center justify-between">
              <div>
                <span className="text-[11px] font-bold text-slate-500 uppercase">{stat.label}</span>
                <p className="text-3xl font-black text-slate-900">{stat.val}</p>
              </div>
              <div className={cn("p-3 rounded-xl border", stat.style)}>
                <stat.icon size={22} />
              </div>
            </div>
          ))}
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
                    activeFilter === f ? "bg-blue-700 text-white" : "text-slate-500 hover:text-slate-900"
                  )}
                >
                  {f}
                </button>
              ))}
            </div>
            <div className="relative w-full md:w-80">
              <Search className="absolute left-3.5 top-3 text-slate-400" size={16} />
              <input
                className="w-full bg-white border border-slate-300 rounded-xl py-2.5 pl-10 pr-4 outline-none text-sm text-slate-900 placeholder-slate-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition"
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
                  onClick={() => handleToggleComplete(item.id)}
                  className={cn(
                    "border border-slate-200 p-4 rounded-xl flex items-start gap-4 cursor-pointer transition",
                    item.status === "Selesai" ? "bg-slate-50 opacity-50" : "hover:bg-slate-50 hover:border-slate-300"
                  )}
                >
                  {item.status === "Selesai" ? (
                    <CheckCircle2 className="text-emerald-400 mt-0.5 shrink-0" size={20} />
                  ) : (
                    <Square className={cn("mt-0.5 shrink-0", item.status === "Terlambat" ? "text-rose-400/40" : "text-blue-600/40")} size={20} />
                  )}
                  <div className="flex-1 min-w-0">
                    <p className={cn("text-sm font-semibold text-slate-900 truncate", item.status === "Selesai" && "line-through text-slate-500")}>
                      {item.task}
                    </p>
                    <div className="flex flex-wrap gap-3 mt-2 text-[11px] text-slate-500 items-center">
                      <span className="flex items-center gap-1"><Users size={12} /> {item.assignee}</span>
                      {item.dueDate && (
                        <span className="flex items-center gap-1"><Clock size={12} /> {formatDateDisplay(item.dueDate)}</span>
                      )}
                      <span className="flex items-center gap-1 bg-blue-50 px-2 py-0.5 rounded text-blue-600 font-medium">
                        <Video size={11} /> {item.meetingTitle}
                      </span>
                      <span className={cn(
                        "px-2 py-0.5 rounded font-bold border text-[10px]",
                        item.status === "Terlambat" && "bg-rose-50 text-rose-600 border-rose-200",
                        item.status === "Aktif" && "bg-blue-50 text-blue-700 border-blue-200",
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
