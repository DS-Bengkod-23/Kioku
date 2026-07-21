"use client";

import React, { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import { ArrowLeft, Users, MapPin, Trash2, FileText, AlertTriangle } from "lucide-react";
import { extractApiError } from "@/lib/utils";
import { useAdminMeetings, useRequestMeetingAccess, useAdminDeleteMeeting } from "@/hooks/useAdmin";
import type { MeetingAdminResponse, MeetingContentAccessResponse } from "@/types";

function formatDate(iso: string) {
    return new Date(iso).toLocaleDateString("id-ID", {
        weekday: "long", day: "numeric", month: "long", year: "numeric", hour: "2-digit", minute: "2-digit",
    });
}

export default function AdminMeetingDetailPage() {
    const { id } = useParams<{ id: string }>();
    const router = useRouter();

    // Gak ada endpoint GET /admin/meetings/{id} tersendiri di kontrak
    // (plan/admin-role-frontend-handoff.md) — cari dari list yang sudah di-fetch.
    const { data, isLoading } = useAdminMeetings();
    const meetings: MeetingAdminResponse[] = data?.items ?? data ?? [];
    const meeting = meetings.find((m) => m.id === id);

    const { mutate: requestAccess, isPending: isRequesting } = useRequestMeetingAccess();
    const { mutateAsync: deleteMeeting, isPending: isDeleting } = useAdminDeleteMeeting();

    const [reason, setReason] = useState("");
    // SENGAJA state lokal, bukan react-query cache — tiap "buka isi" harus jadi
    // request baru (1 baris audit log baru tiap kali), jangan reuse hasil lama.
    const [content, setContent] = useState<MeetingContentAccessResponse | null>(null);

    const handleRequestAccess = () => {
        if (!reason.trim()) {
            toast.error("Isi alasan akses dulu.");
            return;
        }
        requestAccess(
            { meetingId: id, reason: reason.trim() },
            {
                onSuccess: (data) => {
                    setContent(data);
                    toast.success("Akses isi meeting diberikan.");
                },
                onError: (err) => toast.error(extractApiError(err, "Gagal meminta akses isi meeting.")),
            }
        );
    };

    const handleDeleteMeeting = async () => {
        if (!window.confirm("Hapus rapat ini? Aksi ini tercatat di audit log.")) return;
        try {
            await deleteMeeting(id);
            toast.success("Rapat dihapus.");
            router.replace("/admin/meetings");
        } catch (err) {
            toast.error(extractApiError(err, "Gagal menghapus rapat."));
        }
    };

    if (isLoading) {
        return <div className="p-8 text-center text-slate-500 text-xs">Memuat...</div>;
    }

    if (!meeting) {
        return (
            <div className="max-w-3xl mx-auto px-6 py-8 text-center space-y-3">
                <p className="text-sm text-slate-500">Rapat tidak ditemukan.</p>
                <Link href="/admin/meetings" className="text-indigo-600 text-xs hover:underline">← Kembali ke daftar rapat</Link>
            </div>
        );
    }

    return (
        <div className="max-w-4xl mx-auto px-6 py-8 space-y-6">
            <Link href="/admin/meetings" className="inline-flex items-center gap-2 text-slate-500 hover:text-slate-900 text-xs font-medium">
                <ArrowLeft size={14} /> Kembali ke daftar rapat
            </Link>

            <div className="bg-white border border-slate-200 shadow-sm rounded-2xl p-6 space-y-4">
                <div className="flex items-start justify-between gap-4">
                    <div>
                        <h1 className="text-lg font-bold text-slate-900">{meeting.title}</h1>
                        <p className="text-xs text-slate-500 mt-1">{formatDate(meeting.scheduled_at)}</p>
                    </div>
                    <button
                        onClick={handleDeleteMeeting}
                        disabled={isDeleting}
                        className="flex items-center gap-1.5 text-xs font-semibold text-rose-500 hover:text-rose-600 border border-rose-200 hover:bg-rose-50 px-3 py-1.5 rounded-lg transition disabled:opacity-50 shrink-0"
                    >
                        <Trash2 size={13} /> Hapus Rapat
                    </button>
                </div>

                <div className="text-xs text-slate-600 space-y-2 pt-3 border-t border-slate-100">
                    <p className="flex items-center gap-2"><MapPin size={13} className="text-slate-400" /> Organizer: {meeting.organizer_name} ({meeting.organizer_email})</p>
                    <p className="flex items-center gap-2"><Users size={13} className="text-slate-400" /> {meeting.participants.length} peserta</p>
                </div>

                <div className="pt-3 border-t border-slate-100">
                    <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-2">Peserta</p>
                    <div className="space-y-1.5">
                        {meeting.participants.map((p, i) => (
                            <div key={i} className="flex items-center justify-between text-xs">
                                <span className="text-slate-700">{p.name ?? p.email} <span className="text-slate-400">({p.role})</span></span>
                                <span className="text-slate-500">{p.attendance_status ?? "–"}</span>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* Akses isi meeting — alasan wajib diisi ULANG tiap kali, gak ada state "sudah request" yang disimpan */}
            <div className="bg-white border border-slate-200 shadow-sm rounded-2xl p-6 space-y-4">
                <div className="flex items-center gap-2">
                    <FileText size={16} className="text-indigo-600" />
                    <h2 className="text-sm font-bold text-slate-900">Akses Isi Rapat (Transkrip/Notulen)</h2>
                </div>
                <div className="flex items-start gap-2 bg-amber-50 border border-amber-100 rounded-xl p-3 text-[11px] text-amber-700">
                    <AlertTriangle size={14} className="shrink-0 mt-0.5" />
                    <span>Setiap kali kamu buka isi rapat ini, itu tercatat sebagai baris baru di audit log — termasuk kalau kamu sudah pernah buka sebelumnya.</span>
                </div>

                <div className="space-y-2">
                    <label className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Alasan Akses</label>
                    <textarea
                        rows={2}
                        value={reason}
                        onChange={(e) => setReason(e.target.value)}
                        placeholder="Contoh: verifikasi laporan compliance Q3"
                        className="w-full bg-white border border-slate-300 rounded-xl py-2.5 px-4 outline-none text-sm text-slate-900 placeholder-slate-400 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/20 transition resize-none"
                    />
                </div>
                <button
                    onClick={handleRequestAccess}
                    disabled={isRequesting}
                    className="px-5 py-2.5 rounded-xl text-xs font-bold bg-indigo-600 text-white hover:bg-indigo-700 transition disabled:opacity-60"
                >
                    {isRequesting ? "Membuka akses..." : "Buka Isi Rapat"}
                </button>

                {content && (
                    <div className="pt-4 border-t border-slate-200 space-y-3 animate-in fade-in-0 duration-200">
                        {content.summary_tldr && (
                            <div>
                                <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1">Ringkasan</p>
                                <p className="text-xs text-slate-700">{content.summary_tldr}</p>
                            </div>
                        )}
                        {content.summary_decisions && content.summary_decisions.length > 0 && (
                            <div>
                                <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1">Keputusan</p>
                                <ul className="list-disc list-inside text-xs text-slate-700 space-y-0.5">
                                    {content.summary_decisions.map((d, i) => <li key={i}>{d}</li>)}
                                </ul>
                            </div>
                        )}
                        {content.transcript_segments && content.transcript_segments.length > 0 && (
                            <div>
                                <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1">Transkrip</p>
                                <div className="max-h-64 overflow-y-auto space-y-1.5 text-xs text-slate-700 bg-slate-50 rounded-xl p-3">
                                    {content.transcript_segments.map((s: any, i: number) => (
                                        <p key={i}><span className="font-bold">{s.speaker}:</span> {s.text}</p>
                                    ))}
                                </div>
                            </div>
                        )}
                        {!content.summary_tldr && !content.transcript_segments?.length && (
                            <p className="text-xs text-slate-400 italic">Belum ada notulen/transkrip untuk rapat ini.</p>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}
