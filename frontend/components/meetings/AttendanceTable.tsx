"use client";

import React from "react";
import { CheckCircle2, XCircle, Clock, Check, X, User } from "lucide-react";
import { cn } from "@/lib/utils";

interface ParticipantAttendance {
  id: string;
  name: string;
  email: string;
  status: "Hadir" | "Tidak Hadir" | "Belum Hadir";
  rawStatus: string;
}

interface AttendanceTableProps {
  participants: ParticipantAttendance[];
  onMarkAttendance?: (id: string, newStatus: "hadir" | "tidak_hadir") => void;
}

const statusStyle = {
  "Hadir": {
    avatar: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    badge: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    icon: <CheckCircle2 size={9} />,
  },
  "Tidak Hadir": {
    avatar: "bg-red-500/10 text-red-400 border-red-500/20",
    badge: "bg-red-500/10 text-red-400 border-red-500/20",
    icon: <XCircle size={9} />,
  },
  "Belum Hadir": {
    avatar: "bg-amber-500/10 text-amber-400 border-amber-500/20",
    badge: "bg-amber-500/10 text-amber-400 border-amber-500/20",
    icon: <Clock size={9} />,
  },
};

export default function AttendanceTable({ participants, onMarkAttendance }: AttendanceTableProps) {
  return (
    <div className="w-full space-y-4">
      <div className="flex items-center justify-between border-b border-white/5 pb-2">
        <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
          Status Kehadiran
        </h3>
        <span className="text-[10px] px-2 py-0.5 bg-purple-500/10 border border-purple-500/20 rounded-md text-purple-400 font-mono">
          {participants.filter(p => p.status === "Hadir").length}/{participants.length} Hadir
        </span>
      </div>

      <div className="space-y-2 max-h-[280px] overflow-y-auto pr-1 custom-scrollbar">
        {participants.map((participant) => {
          const style = statusStyle[participant.status] ?? statusStyle["Belum Hadir"];
          return (
            <div
              key={participant.id}
              className="flex items-center justify-between p-3 bg-white/[0.02] border border-white/5 rounded-xl"
            >
              <div className="flex items-center gap-2.5 min-w-0 flex-1">
                <div className={cn("w-7 h-7 rounded-full flex items-center justify-center shrink-0 border", style.avatar)}>
                  <User size={12} />
                </div>
                <div className="min-w-0">
                  <p className="text-xs font-semibold text-slate-200 truncate">{participant.name}</p>
                  <p className="text-[10px] text-slate-500 font-mono truncate">{participant.email}</p>
                </div>
              </div>

              <div className="flex items-center gap-1.5 shrink-0 ml-2">
                <span className={cn(
                  "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[9px] font-bold tracking-wide border",
                  style.badge
                )}>
                  {style.icon}
                  {participant.status}
                </span>

                {onMarkAttendance && (
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => onMarkAttendance(participant.id, "hadir")}
                      disabled={participant.status === "Hadir"}
                      title="Tandai Hadir"
                      className="w-6 h-6 rounded-lg flex items-center justify-center bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 hover:bg-emerald-500/20 disabled:opacity-30 disabled:cursor-not-allowed transition"
                    >
                      <Check size={11} />
                    </button>
                    <button
                      onClick={() => onMarkAttendance(participant.id, "tidak_hadir")}
                      disabled={participant.status === "Tidak Hadir"}
                      title="Tandai Tidak Hadir"
                      className="w-6 h-6 rounded-lg flex items-center justify-center bg-red-500/10 text-red-400 border border-red-500/20 hover:bg-red-500/20 disabled:opacity-30 disabled:cursor-not-allowed transition"
                    >
                      <X size={11} />
                    </button>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {onMarkAttendance && (
        <p className="text-[10px] text-slate-600 text-center">
          ✓ = Tandai Hadir &nbsp;·&nbsp; ✗ = Tandai Tidak Hadir
        </p>
      )}
    </div>
  );
}
