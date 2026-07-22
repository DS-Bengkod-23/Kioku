"use client";

import React from "react";
import Link from "next/link";
import { Video, Users as UsersIcon, ClipboardList } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAdminMeetings } from "@/hooks/useAdmin";
import type { MeetingAdminResponse } from "@/types";

function formatDate(iso: string) {
    return new Date(iso).toLocaleDateString("id-ID", {
        day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit",
    });
}

export default function AdminMeetingsPage() {
    const { data, isLoading, isError } = useAdminMeetings();
    const meetings: MeetingAdminResponse[] = data?.items ?? data ?? [];

    return (
        <div className="max-w-6xl mx-auto px-6 py-8 space-y-6">
            <div>
                <h1 className="font-display text-xl font-bold text-slate-900 flex items-center gap-2.5">
                    <Video className="text-slate-700" size={20} /> Audit Rapat
                </h1>
                <p className="text-slate-500 text-sm mt-1">
                    Metadata semua rapat di sistem. Isi (transkrip/notulen) perlu diminta terpisah dengan alasan.
                </p>
            </div>

            <div className="bg-white border border-slate-200 shadow-sm rounded-2xl overflow-hidden">
                {isLoading ? (
                    <div className="p-8 space-y-2">
                        {[...Array(4)].map((_, i) => (
                            <div key={i} className="h-14 rounded-xl bg-slate-100 animate-pulse" />
                        ))}
                    </div>
                ) : isError ? (
                    <p className="text-center text-rose-400 py-10 text-sm">Gagal memuat daftar rapat.</p>
                ) : meetings.length === 0 ? (
                    <p className="text-center text-slate-400 py-10 text-sm italic">Belum ada rapat.</p>
                ) : (
                    <div className="divide-y divide-slate-100">
                        {meetings.map((m) => (
                            <Link
                                key={m.id}
                                href={`/admin/meetings/${m.id}`}
                                className="flex items-center justify-between gap-4 px-6 py-4 hover:bg-slate-50 transition"
                            >
                                <div className="min-w-0">
                                    <p className="text-sm font-bold text-slate-900 truncate">{m.title}</p>
                                    <p className="text-xs text-slate-500 mt-0.5">
                                        {formatDate(m.scheduled_at)} &middot; {m.organizer_name}
                                    </p>
                                </div>
                                <div className="flex items-center gap-4 shrink-0 text-xs text-slate-500">
                                    <span className="flex items-center gap-1"><UsersIcon size={12} /> {m.participants.length}</span>
                                    <span className="flex items-center gap-1"><ClipboardList size={12} /> {m.action_items.done}/{m.action_items.open + m.action_items.done}</span>
                                    <span
                                        className={cn(
                                            "text-[10px] font-bold uppercase tracking-wide px-2 py-1 rounded-full",
                                            m.status === "completed" ? "bg-emerald-50 text-emerald-700" :
                                            m.status === "cancelled" ? "bg-rose-50 text-rose-600" : "bg-indigo-50 text-indigo-700"
                                        )}
                                    >
                                        {m.status}
                                    </span>
                                </div>
                            </Link>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
