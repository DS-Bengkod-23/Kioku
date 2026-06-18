"use client";

import React, { useState } from "react";
import { CheckCircle2, Square, Users, Clock, Plus, X } from "lucide-react";
import { cn } from "@/lib/utils";

interface ActionItem {
  id: string | number;
  task: string;
  assignee: string;
  assigneeId?: string | null;
  dueDate?: string;
  status: "Aktif" | "Terlambat" | "Selesai";
  priority: "Tinggi" | "Sedang" | "Rendah";
}

interface ActionItemListProps {
  items: ActionItem[];
  onToggle: (id: string | number) => void;
  participants?: { id: string; name: string }[];
  onAssign?: (id: string | number, assigneeId: string) => void;
  onAdd?: (data: { task: string; assigneeParticipantId: string | null; dueDate: string | null }) => void;
}

const PRIORITY_STYLE = {
  Tinggi: "bg-red-50 text-red-700 border-red-200",
  Sedang: "bg-blue-50 text-blue-700 border-blue-200",
  Rendah: "bg-slate-50 text-slate-500 border-slate-200",
};

export default function ActionItemList({ items, onToggle, participants, onAssign, onAdd }: ActionItemListProps) {
  const [showForm, setShowForm] = useState(false);
  const [newTask, setNewTask] = useState("");
  const [newAssignee, setNewAssignee] = useState("");
  const [newDueDate, setNewDueDate] = useState("");

  const formatShortDate = (dateStr?: string) => {
    if (!dateStr) return "";
    return new Date(dateStr).toLocaleDateString("id-ID", { day: "numeric", month: "short" });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTask.trim() || !onAdd) return;
    onAdd({
      task: newTask.trim(),
      assigneeParticipantId: newAssignee || null,
      dueDate: newDueDate || null,
    });
    setNewTask("");
    setNewAssignee("");
    setNewDueDate("");
    setShowForm(false);
  };

  return (
    <div className="space-y-2.5">
      {items.map((item) => (
        <div
          key={item.id}
          onClick={() => onToggle(item.id)}
          className={cn(
            "flex items-start gap-3.5 p-4 border border-slate-200 rounded-xl cursor-pointer transition bg-white",
            item.status === "Selesai" ? "bg-slate-50 opacity-50" : "hover:bg-slate-50 hover:border-slate-300"
          )}
        >
          {item.status === "Selesai" ? (
            <CheckCircle2 className="text-emerald-400 mt-0.5 shrink-0" size={18} />
          ) : (
            <Square className={cn("mt-0.5 shrink-0", item.status === "Terlambat" ? "text-rose-400/40" : "text-blue-600/40")} size={18} />
          )}

          <div className="flex-1 min-w-0">
            <p className={cn("text-xs font-semibold text-slate-900 truncate", item.status === "Selesai" && "line-through text-slate-500")}>
              {item.task}
            </p>
            <div className="flex items-center gap-3 mt-1.5 text-[10px] text-slate-500">
              {onAssign ? (
                <span className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                  <Users size={11} />
                  <select
                    value={item.assigneeId ?? ""}
                    onChange={(e) => onAssign(item.id, e.target.value)}
                    className="bg-transparent text-[10px] text-slate-500 border-none focus:outline-none cursor-pointer"
                  >
                    <option value="">Belum di-assign</option>
                    {participants?.map((p) => (
                      <option key={p.id} value={p.id}>{p.name}</option>
                    ))}
                  </select>
                </span>
              ) : (
                <span className="flex items-center gap-1"><Users size={11} /> {item.assignee}</span>
              )}
              {item.dueDate && (
                <span className="flex items-center gap-1"><Clock size={11} /> {formatShortDate(item.dueDate)}</span>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            {item.status === "Terlambat" && (
              <span className="text-[9px] font-bold px-1.5 py-0.5 bg-rose-50 border border-rose-200 text-rose-600 rounded">
                Terlambat
              </span>
            )}
            <span className={cn("text-[9px] font-bold px-2 py-0.5 rounded border", PRIORITY_STYLE[item.priority])}>
              {item.priority}
            </span>
          </div>
        </div>
      ))}

      {/* Form tambah manual */}
      {onAdd && (
        showForm ? (
          <form
            onSubmit={handleSubmit}
            onClick={(e) => e.stopPropagation()}
            className="border border-blue-200 bg-blue-50/40 rounded-xl p-4 space-y-3"
          >
            <input
              type="text"
              placeholder="Nama tugas..."
              value={newTask}
              onChange={(e) => setNewTask(e.target.value)}
              className="w-full text-xs px-3 py-2 rounded-lg border border-slate-200 bg-white focus:outline-none focus:border-blue-400"
              autoFocus
              required
            />
            <div className="flex gap-2">
              {participants && participants.length > 0 && (
                <select
                  value={newAssignee}
                  onChange={(e) => setNewAssignee(e.target.value)}
                  className="flex-1 text-xs px-3 py-2 rounded-lg border border-slate-200 bg-white focus:outline-none focus:border-blue-400 text-slate-600"
                >
                  <option value="">Assign ke... (opsional)</option>
                  {participants.map((p) => (
                    <option key={p.id} value={p.id}>{p.name}</option>
                  ))}
                </select>
              )}
              <input
                type="date"
                value={newDueDate}
                onChange={(e) => setNewDueDate(e.target.value)}
                className="text-xs px-3 py-2 rounded-lg border border-slate-200 bg-white focus:outline-none focus:border-blue-400 text-slate-600"
              />
            </div>
            <div className="flex gap-2 justify-end">
              <button
                type="button"
                onClick={() => { setShowForm(false); setNewTask(""); setNewAssignee(""); setNewDueDate(""); }}
                className="flex items-center gap-1 text-[11px] text-slate-500 hover:text-slate-700 px-3 py-1.5 rounded-lg border border-slate-200 bg-white transition"
              >
                 Batal
              </button>
              <button
                type="submit"
                disabled={!newTask.trim()}
                className="flex items-center gap-1 text-[11px] text-white bg-blue-700 hover:bg-blue-800 px-3 py-1.5 rounded-lg transition disabled:opacity-50"
              >
                 Tambah
              </button>
            </div>
          </form>
        ) : (
          <button
            onClick={() => setShowForm(true)}
            className="w-full flex items-center justify-center gap-1.5 text-[11px] text-slate-400 hover:text-blue-600 hover:border-blue-300 border border-dashed border-slate-200 rounded-xl py-3 transition"
          >
            <Plus size={13} /> Tambah action item manual
          </button>
        )
      )}
    </div>
  );
}
