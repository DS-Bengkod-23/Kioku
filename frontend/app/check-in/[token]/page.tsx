"use client";

import { useEffect, useState } from "react";
import {
  Video,
  CheckCircle2,
  ArrowRight,
  AlertCircle,
  Clock,
  MapPin,
  FileText,
  ListChecks,
  Loader2,
  Lock,
  Download,
} from "lucide-react";
import { getCheckin, confirmCheckin, updateCheckinActionItem, downloadCheckinNotulenPdf } from "@/lib/api";

interface CheckInPageProps {
  params: { token: string };
}

interface ActionItem {
  id: string;
  task: string;
  due_date?: string | null;
  status: "open" | "done";
}

interface Summary {
  tldr: string;
  decisions: string[];
  topics: string[];
}

interface MeetingInfo {
  meeting_id: string;
  meeting_title: string;
  scheduled_at: string;
  location: string;
  participant_name: string;
  already_checked_in: boolean;
  attendance_locked?: boolean;
  processing_status?: string | null;
  summary?: Summary | null;
  action_items?: ActionItem[];
}

const IN_PROGRESS_STATUSES = ["queued", "transcribing", "diarizing", "extracting", "sending_email"];

const PROCESSING_LABEL: Record<string, string> = {
  queued: "Menunggu antrian...",
  transcribing: "Sedang transkripsi audio...",
  diarizing: "Mengidentifikasi pembicara...",
  extracting: "Membuat ringkasan...",
  sending_email: "Mengirim notulen...",
};

export default function CheckInPage({ params }: CheckInPageProps) {
  const [meetingInfo, setMeetingInfo] = useState<MeetingInfo | null>(null);
  const [tokenError, setTokenError] = useState(false);
  const [checkedIn, setCheckedIn] = useState(false);
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);

  // Local action items state for optimistic toggle
  const [actionItems, setActionItems] = useState<ActionItem[]>([]);
  // Track which item ids are being toggled
  const [togglingIds, setTogglingIds] = useState<Set<string>>(new Set());

  // PDF download state
  const [pdfDownloading, setPdfDownloading] = useState(false);

  useEffect(() => {
    getCheckin(params.token)
      .then((data) => {
        setMeetingInfo(data);
        if (data.already_checked_in) setCheckedIn(true);
        if (data.action_items) {
          setActionItems(data.action_items);
        }
      })
      .catch(() => setTokenError(true))
      .finally(() => setInitialLoading(false));
  }, [params.token]);

  const handleCheckIn = async () => {
    setLoading(true);
    try {
      await confirmCheckin(params.token);
      setCheckedIn(true);
    } catch {
      setTokenError(true);
    } finally {
      setLoading(false);
    }
  };

  const handleToggleActionItem = async (item: ActionItem) => {
    if (togglingIds.has(item.id)) return;
    const newStatus = item.status === "done" ? "open" : "done";

    // Optimistic update
    setActionItems((prev) =>
      prev.map((a) => (a.id === item.id ? { ...a, status: newStatus } : a))
    );
    setTogglingIds((prev) => new Set(prev).add(item.id));

    try {
      await updateCheckinActionItem(params.token, item.id, newStatus);
    } catch {
      // Revert on error
      setActionItems((prev) =>
        prev.map((a) => (a.id === item.id ? { ...a, status: item.status } : a))
      );
    } finally {
      setTogglingIds((prev) => {
        const next = new Set(prev);
        next.delete(item.id);
        return next;
      });
    }
  };

  const handleDownloadPdf = async () => {
    if (!meetingInfo) return;
    setPdfDownloading(true);
    try {
      await downloadCheckinNotulenPdf(params.token, meetingInfo.meeting_title);
    } catch {
      // silently fail — user can retry
    } finally {
      setPdfDownloading(false);
    }
  };

  const formatDate = (iso: string) =>
    new Date(iso).toLocaleDateString("id-ID", {
      weekday: "long",
      day: "numeric",
      month: "long",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });

  const notulenReady =
    meetingInfo?.processing_status === "done" || meetingInfo?.processing_status === "completed";

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans flex flex-col">
      {/* Header */}
      <header className="bg-white border-b border-slate-100 sticky top-0 z-10">
        <div className="max-w-xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="h-7 w-7 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-md shadow-indigo-500/20">
              <Video size={13} className="text-white" />
            </div>
            <span className="font-bold text-sm text-slate-900 tracking-wide">MeetMate</span>
          </div>
          <span className="text-xs text-slate-400 font-medium">Portal Peserta</span>
        </div>
      </header>

      {/* Main */}
      <main className="flex-1 max-w-xl mx-auto w-full px-4 py-8 space-y-4">

        {/* Loading */}
        {initialLoading && (
          <div className="flex flex-col items-center py-24 gap-3 text-slate-400">
            <Loader2 size={28} className="animate-spin text-indigo-400" />
            <p className="text-sm">Memvalidasi undangan...</p>
          </div>
        )}

        {/* Token error */}
        {!initialLoading && tokenError && (
          <div className="bg-white border border-slate-200 rounded-2xl p-10 text-center flex flex-col items-center gap-3 shadow-sm">
            <div className="h-14 w-14 rounded-full bg-rose-50 text-rose-400 flex items-center justify-center">
              <AlertCircle size={28} />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-900 mb-1">Link Tidak Valid</h2>
              <p className="text-sm text-slate-400">Link undangan ini sudah tidak berlaku atau tidak ditemukan.</p>
            </div>
          </div>
        )}

        {/* Portal content */}
        {!initialLoading && !tokenError && meetingInfo && (
          <>
            {/* Meeting hero card */}
            <div className="bg-gradient-to-br from-indigo-600 via-violet-600 to-purple-600 rounded-2xl p-6 text-white shadow-lg shadow-indigo-500/20 relative overflow-hidden">
              <div className="absolute inset-0 opacity-10" style={{ backgroundImage: "radial-gradient(circle at 80% 20%, white 0%, transparent 60%)" }} />
              <div className="relative space-y-3">
                <p className="text-indigo-200 text-xs font-semibold uppercase tracking-widest">Undangan Rapat</p>
                <h1 className="text-xl font-bold leading-snug">{meetingInfo.meeting_title}</h1>
                <div className="flex flex-col gap-1.5 text-sm text-indigo-100">
                  <span className="flex items-center gap-2">
                    <Clock size={13} className="shrink-0 text-indigo-300" />
                    {formatDate(meetingInfo.scheduled_at)}
                  </span>
                  {meetingInfo.location && (
                    <span className="flex items-center gap-2">
                      <MapPin size={13} className="shrink-0 text-indigo-300" />
                      {meetingInfo.location}
                    </span>
                  )}
                </div>
                <div className="pt-2 border-t border-white/20">
                  <p className="text-sm text-indigo-100">
                    Halo, <span className="font-bold text-white">{meetingInfo.participant_name}</span>! 👋
                  </p>
                </div>
              </div>
            </div>

            {/* KARTU 1: PRESENSI */}
            <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
              <div className="px-5 py-3.5 border-b border-slate-100 flex items-center gap-2">
                <CheckCircle2 size={14} className="text-indigo-500" />
                <h2 className="text-xs font-bold text-slate-700 uppercase tracking-wider">Presensi</h2>
              </div>
              <div className="p-5">
                {checkedIn ? (
                  <div className="flex items-center gap-4 bg-emerald-50 border border-emerald-100 rounded-xl p-4">
                    <div className="h-10 w-10 rounded-full bg-emerald-500 text-white flex items-center justify-center shrink-0">
                      <CheckCircle2 size={20} />
                    </div>
                    <div>
                      <p className="text-sm font-bold text-emerald-700">Kehadiran Tercatat</p>
                      <p className="text-xs text-emerald-600 mt-0.5">Terima kasih sudah hadir di rapat ini.</p>
                    </div>
                  </div>
                ) : meetingInfo.attendance_locked ? (
                  <div className="flex items-center gap-4 bg-slate-50 border border-slate-200 rounded-xl p-4">
                    <div className="h-10 w-10 rounded-full bg-slate-200 text-slate-500 flex items-center justify-center shrink-0">
                      <Lock size={18} />
                    </div>
                    <div>
                      <p className="text-sm font-bold text-slate-600">Presensi Ditutup</p>
                      <p className="text-xs text-slate-400 mt-0.5">Waktu check-in sudah berakhir.</p>
                    </div>
                  </div>
                ) : (
                  <button
                    onClick={handleCheckIn}
                    disabled={loading}
                    className="w-full bg-gradient-to-r from-indigo-500 to-violet-600 hover:from-indigo-400 hover:to-violet-500 disabled:opacity-60 text-white font-semibold text-sm py-3.5 px-4 rounded-xl transition-all shadow-md shadow-indigo-500/20 flex items-center justify-center gap-2"
                  >
                    {loading ? (
                      <Loader2 size={16} className="animate-spin" />
                    ) : (
                      <><CheckCircle2 size={15} /> Check In Sekarang</>
                    )}
                  </button>
                )}
              </div>
            </div>

            {/* KARTU 2: NOTULEN */}
            <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
              <div className="px-5 py-3.5 border-b border-slate-100 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <FileText size={14} className="text-indigo-500" />
                  <h2 className="text-xs font-bold text-slate-700 uppercase tracking-wider">Notulen</h2>
                </div>
                {notulenReady && meetingInfo.summary && (
                  <button
                    onClick={handleDownloadPdf}
                    disabled={pdfDownloading}
                    className="inline-flex items-center gap-1.5 text-xs font-semibold text-indigo-600 hover:text-indigo-800 bg-indigo-50 hover:bg-indigo-100 disabled:opacity-50 px-3 py-1.5 rounded-lg transition"
                  >
                    {pdfDownloading ? <Loader2 size={11} className="animate-spin" /> : <Download size={11} />}
                    {pdfDownloading ? "Mengunduh..." : "Unduh PDF"}
                  </button>
                )}
              </div>
              <div className="p-5">
                {!meetingInfo.processing_status ? (
                  <div className="text-center py-6 text-slate-400">
                    <FileText size={28} className="mx-auto mb-2 opacity-30" />
                    <p className="text-sm">Rekaman rapat belum diupload.</p>
                  </div>
                ) : IN_PROGRESS_STATUSES.includes(meetingInfo.processing_status) ? (
                  <div className="flex items-center gap-3 bg-indigo-50 border border-indigo-100 rounded-xl p-4">
                    <Loader2 size={18} className="animate-spin text-indigo-500 shrink-0" />
                    <div>
                      <p className="text-sm font-medium text-indigo-700">Sedang Diproses</p>
                      <p className="text-xs text-indigo-500 mt-0.5">{PROCESSING_LABEL[meetingInfo.processing_status] ?? "Sedang diproses..."}</p>
                    </div>
                  </div>
                ) : meetingInfo.processing_status === "failed" ? (
                  <div className="flex items-center gap-3 bg-rose-50 border border-rose-100 rounded-xl p-4">
                    <AlertCircle size={18} className="text-rose-400 shrink-0" />
                    <p className="text-sm text-rose-600">Pemrosesan rekaman gagal.</p>
                  </div>
                ) : meetingInfo.summary ? (
                  <div className="space-y-4">
                    <div className="bg-slate-50 rounded-xl p-4">
                      <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">Ringkasan</p>
                      <p className="text-sm text-slate-700 leading-relaxed">{meetingInfo.summary.tldr}</p>
                    </div>
                    {meetingInfo.summary.decisions.length > 0 && (
                      <div>
                        <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">Keputusan</p>
                        <ul className="space-y-1.5">
                          {meetingInfo.summary.decisions.map((d, i) => (
                            <li key={i} className="text-sm text-slate-700 flex gap-2">
                              <span className="text-indigo-400 shrink-0 mt-0.5">•</span> {d}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {meetingInfo.summary.topics.length > 0 && (
                      <div>
                        <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">Topik</p>
                        <div className="flex flex-wrap gap-1.5">
                          {meetingInfo.summary.topics.map((t, i) => (
                            <span key={i} className="px-2.5 py-1 bg-indigo-50 text-indigo-600 border border-indigo-100 rounded-full text-xs font-medium">{t}</span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="text-center py-6 text-slate-400">
                    <FileText size={28} className="mx-auto mb-2 opacity-30" />
                    <p className="text-sm">Notulen belum tersedia.</p>
                  </div>
                )}
              </div>
            </div>

            {/* KARTU 3: ACTION ITEMS */}
            <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
              <div className="px-5 py-3.5 border-b border-slate-100 flex items-center gap-2">
                <ListChecks size={14} className="text-indigo-500" />
                <h2 className="text-xs font-bold text-slate-700 uppercase tracking-wider">Action Items Saya</h2>
                {actionItems.length > 0 && (
                  <span className="ml-auto text-[10px] font-bold bg-indigo-50 text-indigo-600 border border-indigo-100 px-2 py-0.5 rounded-full">
                    {actionItems.filter(a => a.status === "done").length}/{actionItems.length} selesai
                  </span>
                )}
              </div>
              <div className="p-5">
                {actionItems.length === 0 ? (
                  <div className="text-center py-6 text-slate-400">
                    <ListChecks size={28} className="mx-auto mb-2 opacity-30" />
                    <p className="text-sm">Tidak ada action item untuk Anda.</p>
                  </div>
                ) : (
                  <ul className="space-y-2">
                    {actionItems.map((item) => {
                      const isDone = item.status === "done";
                      const isToggling = togglingIds.has(item.id);
                      return (
                        <li
                          key={item.id}
                          className={`flex items-start gap-3 p-3 rounded-xl border transition-all duration-200 ${
                            isDone ? "bg-slate-50 border-slate-100" : "bg-white border-slate-200 hover:border-indigo-200"
                          }`}
                        >
                          <button
                            onClick={() => handleToggleActionItem(item)}
                            disabled={isToggling}
                            title={isDone ? "Tandai sebagai Open" : "Tandai sebagai Selesai"}
                            className={`mt-0.5 shrink-0 h-5 w-5 rounded-full border-2 flex items-center justify-center transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-1 ${
                              isToggling ? "opacity-50 cursor-wait" : "cursor-pointer"
                            } ${isDone
                              ? "bg-emerald-500 border-emerald-500 text-white focus:ring-emerald-400"
                              : "border-slate-300 hover:border-indigo-400 focus:ring-indigo-400"
                            }`}
                          >
                            {isToggling ? (
                              <Loader2 size={10} className="animate-spin" />
                            ) : isDone ? (
                              <svg width="9" height="7" viewBox="0 0 9 7" fill="none">
                                <path d="M1 3.5L3.5 6L8 1" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                              </svg>
                            ) : null}
                          </button>

                          <div className="flex-1 min-w-0">
                            <p className={`text-sm leading-snug transition-all duration-200 ${
                              isDone ? "line-through text-slate-400" : "text-slate-700 font-medium"
                            }`}>
                              {item.task}
                            </p>
                            {item.due_date && (
                              <p className="text-xs text-slate-400 mt-0.5 flex items-center gap-1">
                                <Clock size={10} />
                                {new Date(item.due_date).toLocaleDateString("id-ID", { day: "numeric", month: "long", year: "numeric" })}
                              </p>
                            )}
                          </div>

                          <button
                            onClick={() => handleToggleActionItem(item)}
                            disabled={isToggling}
                            className={`text-[10px] font-bold px-2 py-0.5 rounded-full shrink-0 transition-all duration-200 border ${
                              isToggling ? "opacity-50 cursor-wait" : "cursor-pointer"
                            } ${isDone
                              ? "bg-emerald-50 text-emerald-600 border-emerald-200"
                              : "bg-slate-50 text-slate-500 border-slate-200 hover:bg-indigo-50 hover:text-indigo-600 hover:border-indigo-200"
                            }`}
                          >
                            {isDone ? "✓ Selesai" : "Open"}
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </div>
            </div>
          </>
        )}
      </main>

      <footer className="py-5 text-center text-[11px] text-slate-400 border-t border-slate-100 bg-white">
        © {new Date().getFullYear()} MeetMate Platform
      </footer>
    </div>
  );
}
