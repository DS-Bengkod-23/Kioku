"use client";

import React, { useState } from "react";
import { ScrollText, ChevronLeft, ChevronRight } from "lucide-react";
import { useAuditLogs } from "@/hooks/useAdmin";
import type { AuditLogResponse } from "@/types";

const LIMIT = 50;

const ACTION_LABEL: Record<string, string> = {
    suspend_user: "Suspend pengguna",
    unsuspend_user: "Aktifkan kembali pengguna",
    promote_user: "Naikkan role pengguna",
    demote_user: "Turunkan role pengguna",
    reset_password: "Kirim reset password",
    request_meeting_access: "Buka isi rapat",
    delete_meeting: "Hapus rapat",
    delete_recording: "Hapus rekaman",
};

function formatDate(iso: string) {
    return new Date(iso).toLocaleString("id-ID", {
        day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit",
    });
}

export default function AdminAuditLogsPage() {
    const [offset, setOffset] = useState(0);
    const { data, isLoading, isError } = useAuditLogs(LIMIT, offset);
    const logs: AuditLogResponse[] = data?.items ?? data ?? [];

    return (
        <div className="max-w-6xl mx-auto px-6 py-8 space-y-6">
            <div>
                <h1 className="font-display text-xl font-bold text-slate-900 flex items-center gap-2.5">
                    <ScrollText className="text-slate-700" size={20} /> Audit Log
                </h1>
                <p className="text-slate-500 text-sm mt-1">
                    Admin biasa cuma lihat aktivitas miliknya sendiri; superadmin lihat semua — ini diatur backend, bukan FE.
                </p>
            </div>

            <div className="bg-white border border-slate-200 shadow-sm rounded-2xl overflow-hidden">
                {isLoading ? (
                    <div className="p-8 space-y-2">
                        {[...Array(5)].map((_, i) => (
                            <div key={i} className="h-10 rounded-xl bg-slate-100 animate-pulse" />
                        ))}
                    </div>
                ) : isError ? (
                    <p className="text-center text-rose-400 py-10 text-sm">Gagal memuat audit log.</p>
                ) : logs.length === 0 ? (
                    <p className="text-center text-slate-400 py-10 text-sm italic">Belum ada aktivitas.</p>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="border-b border-slate-200 text-left text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                                    <th className="px-6 py-3">Waktu</th>
                                    <th className="px-6 py-3">Aksi</th>
                                    <th className="px-6 py-3">Target</th>
                                    <th className="px-6 py-3">Alasan</th>
                                </tr>
                            </thead>
                            <tbody>
                                {logs.map((log) => (
                                    <tr key={log.id} className="border-b border-slate-100 last:border-0">
                                        <td className="px-6 py-3 text-xs text-slate-500 whitespace-nowrap">{formatDate(log.created_at)}</td>
                                        <td className="px-6 py-3 text-xs font-semibold text-slate-900">{ACTION_LABEL[log.action] ?? log.action}</td>
                                        <td className="px-6 py-3 text-xs text-slate-500">{log.target_type} · {log.target_id.slice(0, 8)}</td>
                                        <td className="px-6 py-3 text-xs text-slate-500 max-w-xs truncate">{log.reason ?? "–"}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            <div className="flex items-center justify-center gap-3">
                <button
                    onClick={() => setOffset((o) => Math.max(0, o - LIMIT))}
                    disabled={offset === 0}
                    className="p-2 rounded-xl bg-white border border-slate-200 text-slate-500 hover:text-slate-900 transition shadow-sm disabled:opacity-40"
                >
                    <ChevronLeft size={16} />
                </button>
                <span className="text-xs text-slate-500 font-medium">Halaman {Math.floor(offset / LIMIT) + 1}</span>
                <button
                    onClick={() => setOffset((o) => o + LIMIT)}
                    disabled={logs.length < LIMIT}
                    className="p-2 rounded-xl bg-white border border-slate-200 text-slate-500 hover:text-slate-900 transition shadow-sm disabled:opacity-40"
                >
                    <ChevronRight size={16} />
                </button>
            </div>
        </div>
    );
}
