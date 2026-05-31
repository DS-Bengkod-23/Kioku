"use client";

import React, { useState, useMemo, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  //CheckSquare,
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
import { cn } from "@/lib/utils";

interface ActionItem {
  id: number;
  task: string;
  meetingTitle: string;
  assignee: string;
  dueDate: string; // Format YYYY-MM-DD
  status: "Aktif" | "Terlambat" | "Selesai";
}

export default function ActionItemsPage() {
  const router = useRouter();
  const [mounted, setMounted] = useState(false);

  const [tasks, setTasks] = useState<ActionItem[]>([
    { id: 1, task: "Selesaikan responsive design", meetingTitle: "Weekly Standup", assignee: "Jane Smith", dueDate: "2026-05-20", status: "Terlambat" },
    { id: 2, task: "Setup testing automation", meetingTitle: "Weekly Standup", assignee: "John Doe", dueDate: "2026-05-25", status: "Terlambat" },
    { id: 3, task: "Review dokumentasi API", meetingTitle: "Technical Sync", assignee: "Alice Brown", dueDate: "2026-06-15", status: "Aktif" },
    { id: 4, task: "Slide materi seminar", meetingTitle: "Koordinasi Seminar", assignee: "John Doe", dueDate: "2026-06-05", status: "Selesai" },
  ]);

  const [searchQuery, setSearchQuery] = useState("");
  const [activeFilter, setActiveFilter] = useState<"Semua" | "Aktif" | "Selesai">("Semua");

  // Mencegah Hydration Error akibat format tanggal lokal
  useEffect(() => {
    setMounted(true);
  }, []);

  const handleToggleComplete = (id: number) => {
    setTasks(prevTasks =>
      prevTasks.map(task => {
        if (task.id !== id) return task;
        if (task.status === "Selesai") {
          const isOverdue = new Date(task.dueDate) < new Date();
          return { ...task, status: (isOverdue ? "Terlambat" : "Aktif") as ActionItem["status"] };
        }
        return { ...task, status: "Selesai" as ActionItem["status"] };
      })
    );
  };

  const formatDateDisplay = (dateString: string) => {
    if (!mounted) return dateString;
    return new Date(dateString).toLocaleDateString('id-ID', { day: 'numeric', month: 'short', year: 'numeric' });
  };

  const stats = useMemo(() => ({
    total: tasks.length,
    aktif: tasks.filter(t => t.status !== "Selesai").length,
    selesai: tasks.filter(t => t.status === "Selesai").length
  }), [tasks]);

  const filteredTasks = useMemo(() => {
    const filtered = tasks.filter(task => {
      const matchesSearch = task.task.toLowerCase().includes(searchQuery.toLowerCase()) ||
        task.meetingTitle.toLowerCase().includes(searchQuery.toLowerCase());
      if (activeFilter === "Aktif") return matchesSearch && (task.status === "Aktif" || task.status === "Terlambat");
      if (activeFilter === "Selesai") return matchesSearch && task.status === "Selesai";
      return matchesSearch;
    });

    return filtered.sort((a, b) => {
      const order = { "Terlambat": 0, "Aktif": 1, "Selesai": 2 };
      return order[a.status] - order[b.status];
    });
  }, [tasks, searchQuery, activeFilter]);

  return (
    <main className="bg-[#0A051B] min-h-screen text-slate-100 pb-16 pt-8">
      <div className="max-w-5xl mx-auto px-6 space-y-8">

        {/* Tombol Kembali */}
        <button
          onClick={() => router.back()}
          className="inline-flex items-center gap-2 text-slate-400 hover:text-white transition text-xs font-medium mb-4"
        >
          <ArrowLeft size={16} />
          Kembali ke Dashboard
        </button>

        {/* Header */}
        <div className="space-y-1">
          <h1 className="text-2xl font-bold text-white flex items-center gap-2.5">
            <ClipboardList className="text-[#7E61F2]" size={26} /> Tugas Saya
          </h1>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {[
            { label: "Total Tugas", val: stats.total, icon: ClipboardList, style: "bg-blue-500/10 border-blue-500/20 text-blue-400" },
            { label: "Tugas Aktif", val: stats.aktif, icon: AlertCircle, style: "bg-amber-500/10 border-amber-500/20 text-amber-400" },
            { label: "Tugas Selesai", val: stats.selesai, icon: CheckCircle2, style: "bg-emerald-500/10 border-emerald-500/20 text-emerald-400" },
          ].map((stat, i) => (
            <div key={i} className="bg-[#130E29]/60 p-5 rounded-2xl border border-white/5 flex items-center justify-between">
              <div>
                <span className="text-[11px] font-bold text-slate-400 uppercase">{stat.label}</span>
                <p className="text-3xl font-black text-white">{stat.val}</p>
              </div>
              <div className={cn("p-3 rounded-xl border", stat.style)}>
                <stat.icon size={22} />
              </div>
            </div>
          ))}
        </div>

        {/* Konten Utama */}
        <div className="bg-[#130E29]/40 rounded-2xl p-6 border border-white/5">
          <div className="flex flex-col md:flex-row gap-4 justify-between mb-6">
            <div className="flex bg-[#0A051B] p-1 rounded-xl border border-white/5">
              {(["Semua", "Aktif", "Selesai"] as const).map((f) => (
                <button key={f} onClick={() => setActiveFilter(f)} className={cn("px-6 py-2 rounded-lg text-xs font-bold transition", activeFilter === f ? "bg-[#7E61F2] text-white" : "text-slate-400 hover:text-white")}>
                  {f}
                </button>
              ))}
            </div>
            <div className="relative w-full md:w-80">
              <Search className="absolute left-3.5 top-3 text-slate-500" size={16} />
              <input
                className="w-full bg-[#0A051B] border border-white/10 rounded-xl py-2.5 pl-10 pr-4 outline-none text-sm text-slate-200 focus:border-purple-500/40 transition"
                placeholder="Cari tugas..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
          </div>

          {/* List Item Rapat */}
          <div className="space-y-3">
            {filteredTasks.length > 0 ? (
              filteredTasks.map((item) => (
                <div
                  key={item.id}
                  onClick={() => handleToggleComplete(item.id)}
                  className={cn(
                    "border border-white/5 p-4 rounded-xl flex items-start gap-4 cursor-pointer transition bg-white/[0.01]",
                    item.status === "Selesai" ? "bg-black/20 opacity-50" : "hover:bg-white/5 hover:border-white/10"
                  )}
                >
                  {item.status === "Selesai" ? (
                    <CheckCircle2 className="text-emerald-400 mt-0.5 shrink-0" size={20} />
                  ) : (
                    <Square className={cn("mt-0.5 shrink-0", item.status === "Terlambat" ? "text-rose-400/40" : "text-purple-400/40")} size={20} />
                  )}
                  <div className="flex-1 min-w-0">
                    <p className={cn("text-sm font-semibold text-slate-200 truncate", item.status === "Selesai" && "line-through text-slate-500")}>
                      {item.task}
                    </p>
                    <div className="flex flex-wrap gap-3 mt-2 text-[11px] text-slate-400 items-center">
                      <span className="flex items-center gap-1"><Users size={12} /> {item.assignee}</span>
                      <span className="flex items-center gap-1"><Clock size={12} /> {formatDateDisplay(item.dueDate)}</span>
                      <span className="flex items-center gap-1 bg-purple-500/10 px-2 py-0.5 rounded text-purple-300 font-medium">
                        <Video size={11} /> {item.meetingTitle}
                      </span>
                      <span className={cn(
                        "px-2 py-0.5 rounded font-bold border text-[10px]",
                        item.status === "Terlambat" && "bg-rose-500/10 text-rose-400 border-rose-500/20",
                        item.status === "Aktif" && "bg-blue-500/10 text-blue-400 border-blue-500/20",
                        item.status === "Selesai" && "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
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