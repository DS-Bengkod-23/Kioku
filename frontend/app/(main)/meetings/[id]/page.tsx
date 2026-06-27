"use client";

import React, { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, UserCircle, Calendar, MapPin, Trash2, Download } from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";
import { cn, isDateOverdue } from "@/lib/utils";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";

import UploadZone from "@/components/recording/UploadZone";
import ProcessingStatus from "@/components/recording/ProcessingStatus";
import ActionItemList from "@/components/notulen/ActionItemList";
import SummaryCard from "@/components/notulen/SummaryCard";
import TranscriptView from "@/components/notulen/TranscriptView";
import AttendanceTable from "@/components/meetings/AttendanceTable";


import { useMeeting, useUpdateAttendance, useDeleteMeeting } from "@/hooks/useMeeting";
import { useUploadRecording, useRecordingStatus, useDeleteRecording } from "@/hooks/useRecording";
import { useUpdateActionItem, useCreateActionItem } from "@/hooks/useActionItems";
import { downloadNotulenPdf } from "@/lib/api";

function formatDate(isoString: string) {
  return new Date(isoString).toLocaleDateString("id-ID", {
    weekday: "long", day: "numeric", month: "long", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

export default function MeetingDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<"ringkasan" | "transkrip">("ringkasan");
  const [pollingEnabled, setPollingEnabled] = useState(false);
  const [isDownloadingPdf, setIsDownloadingPdf] = useState(false);

  const { data: meeting, isLoading, isError } = useMeeting(id);
  const { data: recordingStatus } = useRecordingStatus(id, pollingEnabled);
  const { mutateAsync: uploadRecording, isPending: isUploading, progress: uploadProgress } = useUploadRecording(id);
  const { mutateAsync: deleteRecording, isPending: isDeletingRec } = useDeleteRecording(id);

  const recordingFilenameKey = `recording_filename_${id}`;
  const [recordingFileName, setRecordingFileName] = useState<string | null>(null);
  useEffect(() => {
    setRecordingFileName(localStorage.getItem(recordingFilenameKey));
  }, [recordingFilenameKey]);

  // Auto-enable polling saat refresh jika ML masih memproses
  useEffect(() => {
    if (["queued", "transcribing", "diarizing", "extracting", "sending_email"].includes(meeting?.processing_status)) {
      setPollingEnabled(true);
    }
  }, [meeting?.processing_status]);
  const { mutate: updateAttendance } = useUpdateAttendance(id);
  const { mutate: updateActionItem } = useUpdateActionItem(id);
  const { mutateAsync: createActionItem } = useCreateActionItem(id);
  const { mutateAsync: deleteMeeting, isPending: isDeletingMeeting } = useDeleteMeeting();

  // Deteksi apakah user adalah organizer
  // localStorage hanya tersedia di browser (bukan saat SSR)
  const currentUserEmail = typeof window !== "undefined"
    ? JSON.parse(localStorage.getItem("user_profile") || "{}").email
    : null;
  const isOrganizer = meeting?.organizer?.email === currentUserEmail;

  const handleUpload = async (file: File) => {
    const form = new FormData();
    form.append("file", file);
    try {
      await uploadRecording(form);
      localStorage.setItem(recordingFilenameKey, file.name);
      setRecordingFileName(file.name);
      setPollingEnabled(true);
      toast.success("Rekaman berhasil diupload, AI sedang memproses...");
    } catch {
      toast.error("Upload gagal. Coba lagi.");
    }
  };

  const handleDeleteRecording = async () => {
    try {
      await deleteRecording();
      localStorage.removeItem(recordingFilenameKey);
      setRecordingFileName(null);
      setPollingEnabled(false);
      toast.success("Rekaman berhasil dihapus.");
    } catch {
      toast.error("Gagal menghapus rekaman.");
    }
  };

  const handleDeleteMeeting = async () => {
    try {
      await deleteMeeting(id);
      toast.success("Rapat berhasil dihapus.");
      router.push("/meetings");
    } catch {
      toast.error("Gagal menghapus rapat.");
    }
  };

  const handleMarkAttendance = (participantId: string, newStatus: "hadir" | "tidak_hadir") => {
    updateAttendance({ participantId, status: newStatus });
  };

  const handleToggleTask = (taskId: string | number) => {
    const item = meeting?.action_items?.find((a: any) => a.id === taskId);
    if (!item) return;
    const newStatus = item.status === "done" ? "open" : "done";
    updateActionItem({ id: String(taskId), status: newStatus });
  };

  const handleAssignTask = (taskId: string | number, assigneeId: string) => {
    updateActionItem({ id: String(taskId), assigneeId: assigneeId || null });
  };

  const handleDownloadPdf = async () => {
    setIsDownloadingPdf(true);
    try {
      await downloadNotulenPdf(id, meeting?.title ?? id);
    } catch {
      toast.error("Gagal mengunduh notulen PDF.");
    } finally {
      setIsDownloadingPdf(false);
    }
  };

  const handleCreateActionItem = async (data: { task: string; assigneeParticipantId: string | null; dueDate: string | null }) => {
    try {
      await createActionItem({ task: data.task, assignee_participant_id: data.assigneeParticipantId, due_date: data.dueDate });
      toast.success("Action item berhasil ditambahkan.");
    } catch {
      toast.error("Gagal menambahkan action item.");
    }
  };

  // Map participants ke format AttendanceTable
  const attendanceData = (meeting?.participants ?? []).map((p: any) => {
    const rawStatus = p.attendance_status ?? "pending";
    const status =
      rawStatus === "hadir" ? "Hadir" :
      rawStatus === "tidak_hadir" ? "Tidak Hadir" : "Belum Hadir";
    return {
      id: String(p.id),
      name: p.name || p.email?.split("@")[0] || "Tanpa Nama",
      email: p.email,
      status: status as "Hadir" | "Tidak Hadir" | "Belum Hadir",
      rawStatus,
    };
  });

  const getActionItemPriority = (dueDate?: string | null): "Tinggi" | "Sedang" | "Rendah" => {
    if (!dueDate) return "Rendah";
    const diffDays = Math.ceil((new Date(dueDate).getTime() - Date.now()) / 86400000);
    if (diffDays < 0) return "Tinggi";
    if (diffDays <= 3) return "Sedang";
    return "Rendah";
  };

  // Map action items ke format ActionItemList
  const actionItems = (meeting?.action_items ?? []).map((item: any) => {
    const isOverdue = item.due_date && isDateOverdue(item.due_date);
    const status =
      item.status === "done" ? "Selesai" :
      isOverdue ? "Terlambat" : "Aktif";
    return {
      id: item.id,
      task: item.task,
      assignee: item.assignee?.name || "Belum di-assign",
      assigneeId: item.assignee_participant_id ?? null,
      dueDate: item.due_date ?? undefined,
      status,
      priority: getActionItemPriority(item.due_date),
    };
  });

  const participantOptions = (meeting?.participants ?? []).map((p: any) => ({
    id: String(p.id),
    name: p.name || p.email?.split("@")[0] || "Tanpa Nama",
  }));

  // Tentukan status proses rekaman
  const processingStatus = recordingStatus?.processing_status ?? meeting?.processing_status;
  const steps = recordingStatus?.steps;

  const mapProcessStatus = () => {
    if (isUploading) return "uploading";
    if (processingStatus === "completed") return "ready";
    return "processing";
  };

  const hasRecording = !!meeting?.recording;
  const showProcessing = hasRecording || isUploading;
  const isFailed = processingStatus === "failed";
  const processingError = recordingStatus?.error ?? null;

  if (isLoading) {
    return (
      <div className="w-full min-h-screen bg-slate-50 flex items-center justify-center text-slate-500 text-xs font-medium">
        Memuat detail data rapat...
      </div>
    );
  }

  if (isError || !meeting) {
    return (
      <div className="w-full min-h-screen bg-slate-50 flex flex-col items-center justify-center gap-4">
        <p className="text-rose-400 text-sm">Rapat tidak ditemukan atau terjadi kesalahan.</p>
        <Link href="/meetings" className="text-blue-600 text-xs hover:underline">← Kembali ke Dashboard</Link>
      </div>
    );
  }

  return (
    <main className="bg-slate-50 min-h-screen text-slate-900 pb-16 px-6">
      <div className="max-w-7xl mx-auto pt-8">

        <Link href="/meetings" className="inline-flex items-center gap-2 text-slate-500 hover:text-slate-900 transition text-xs font-medium mb-6">
          <ArrowLeft size={16} /> Kembali ke Dashboard
        </Link>

        <div className="flex items-start justify-between mb-8 animate-in fade-in-0 slide-in-from-bottom-3 duration-300">
          <h1 className="text-2xl font-bold text-slate-900">{meeting.title}</h1>
          {isOrganizer && (
            <div className="flex items-center gap-2">
              <Link
                href={`/meetings/${id}/edit`}
                className="text-xs font-semibold text-blue-600 border border-blue-200 px-4 py-2 rounded-xl hover:bg-blue-50 transition"
              >
                Edit Rapat
              </Link>
              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <button className="text-xs font-semibold text-rose-600 border border-rose-200 px-4 py-2 rounded-xl hover:bg-rose-50 transition flex items-center gap-1.5">
                    <Trash2 size={13} /> Hapus Rapat
                  </button>
                </AlertDialogTrigger>
                <AlertDialogContent className="bg-white border border-slate-200 text-slate-900">
                  <AlertDialogHeader>
                    <AlertDialogTitle>Hapus Rapat?</AlertDialogTitle>
                    <AlertDialogDescription className="text-slate-500">
                      Tindakan ini tidak dapat dibatalkan. Semua data rapat termasuk rekaman, transkrip, dan action items akan dihapus secara permanen.
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel className="bg-transparent border border-slate-200 text-slate-700 hover:bg-slate-50 hover:text-slate-900">
                      Batalkan
                    </AlertDialogCancel>
                    <AlertDialogAction
                      onClick={handleDeleteMeeting}
                      disabled={isDeletingMeeting}
                      className="bg-rose-600 hover:bg-rose-500 text-white border-0 disabled:opacity-50"
                    >
                      {isDeletingMeeting ? "Menghapus..." : "Ya, Hapus Rapat"}
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 animate-in fade-in-0 slide-in-from-bottom-3 duration-300 delay-75">

          {/* ====== KOLOM KIRI ====== */}
          <div className="space-y-6">

            {/* Upload Rekaman */}
            {isOrganizer && (
              <section className="bg-white border border-slate-200 shadow-sm rounded-2xl p-6">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-xs font-bold text-blue-700 uppercase tracking-wider">Upload Rekaman</h2>
                  {hasRecording && (
                    <button
                      onClick={handleDeleteRecording}
                      disabled={isDeletingRec}
                      className="text-rose-400 hover:text-rose-300 transition"
                      title="Hapus rekaman"
                    >
                      <Trash2 size={15} />
                    </button>
                  )}
                </div>
                {!showProcessing ? (
                  <UploadZone onUpload={handleUpload} />
                ) : isFailed ? (
                  <div className="rounded-xl bg-rose-50 border border-rose-200 p-4 text-center space-y-2">
                    <p className="text-xs font-bold text-rose-600">Proses gagal</p>
                    {processingError && (
                      <p className="text-[11px] text-rose-500 font-mono break-all">{processingError}</p>
                    )}
                    <button
                      onClick={handleDeleteRecording}
                      disabled={isDeletingRec}
                      className="text-[11px] text-rose-600 hover:text-rose-700 underline transition mt-1"
                    >
                      Hapus dan coba upload ulang
                    </button>
                  </div>
                ) : (
                  <ProcessingStatus
                    status={mapProcessStatus()}
                    progress={isUploading ? uploadProgress : 100}
                    fileName={recordingFileName}
                  />
                )}
                {!isFailed && steps && (
                  <div className="mt-3 space-y-1">
                    {Object.entries(steps).map(([step, val]) => (
                      <div key={step} className="flex items-center justify-between text-[11px] text-slate-500">
                        <span className="capitalize">{step.replace(/_/g, " ")}</span>
                        <span className={cn(
                          val === "completed" ? "text-emerald-700" :
                          val === "in_progress" ? "text-amber-700" : "text-slate-500"
                        )}>{String(val)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </section>
            )}

            {/* Informasi Rapat */}
            <section className="bg-white border border-slate-200 shadow-sm rounded-2xl p-6 space-y-4">
              <h2 className="text-xs font-bold text-blue-700 uppercase tracking-wider border-b border-slate-200 pb-3">Informasi Rapat</h2>
              <div className="text-xs space-y-3.5 text-slate-700">
                <p className="flex items-center gap-2.5"><UserCircle className="text-blue-600" size={15} /> {meeting.organizer?.name}</p>
                <p className="flex items-center gap-2.5"><Calendar className="text-blue-600" size={15} /> {formatDate(meeting.scheduled_at)}</p>
                <p className="flex items-center gap-2.5"><MapPin className="text-blue-600" size={15} /> {meeting.location || "–"}</p>
              </div>
              {meeting.description && (
                <div className="pt-3 border-t border-slate-200 space-y-1.5">
                  <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Deskripsi</p>
                  <p className="text-xs text-slate-700 leading-relaxed">{meeting.description}</p>
                </div>
              )}
              {meeting.agenda_text && (
                <div className="pt-3 border-t border-slate-200 space-y-1.5">
                  <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Agenda</p>
                  <p className="text-xs text-slate-700 leading-relaxed whitespace-pre-line">{meeting.agenda_text}</p>
                </div>
              )}
            </section>

            {/* Kehadiran */}
            <section className="bg-white border border-slate-200 shadow-sm rounded-2xl p-6">
              <AttendanceTable
                participants={attendanceData}
                onMarkAttendance={isOrganizer ? handleMarkAttendance : undefined}
              />
            </section>
          </div>

          {/* ====== KOLOM KANAN ====== */}
          <div className="lg:col-span-2 space-y-6">

            {/* Tab Ringkasan / Transkrip */}
            <section className="bg-white border border-slate-200 shadow-sm rounded-2xl overflow-hidden">
              <div className="flex items-center gap-2 p-1 bg-slate-100 border-b border-slate-200">
                <div className="flex flex-1">
                  {(["ringkasan", "transkrip"] as const).map((tab) => (
                    <button
                      key={tab}
                      onClick={() => setActiveTab(tab)}
                      className={cn("flex-1 py-2.5 text-xs font-bold rounded-xl transition capitalize",
                        activeTab === tab ? "bg-blue-700 text-white" : "text-slate-500 hover:text-slate-700"
                      )}
                    >
                      {tab === "ringkasan" ? "Ringkasan AI" : "Transkrip Audio"}
                    </button>
                  ))}
                </div>
                {processingStatus === "completed" && (
                  <button
                    onClick={handleDownloadPdf}
                    disabled={isDownloadingPdf}
                    className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-white border border-slate-200 text-slate-600 hover:text-blue-700 hover:border-blue-300 text-xs font-semibold transition disabled:opacity-50 shrink-0"
                    title="Download Notulen PDF"
                  >
                    <Download size={13} />
                    {isDownloadingPdf ? "Mengunduh..." : "PDF"}
                  </button>
                )}
              </div>
              <div className="p-6 min-h-[320px]">
                {meeting.summary || meeting.transcript ? (
                  <div className="animate-in fade-in duration-300">
                    {activeTab === "ringkasan" && meeting.summary ? (
                      <SummaryCard summary={{
                        executiveSummary: meeting.summary.tldr,
                        highlights: meeting.summary.decisions ?? [],
                        topics: meeting.summary.topics ?? [],
                      }} />
                    ) : activeTab === "transkrip" && meeting.transcript ? (
                      <TranscriptView lines={(meeting.transcript.segments ?? []).map((s: any) => ({
                        timestamp: `${Math.floor(s.start / 60).toString().padStart(2, "0")}:${Math.floor(s.start % 60).toString().padStart(2, "0")}.0`,
                        speakerId: s.speaker,
                        speakerName: s.speaker,
                        text: s.text,
                      }))} />
                    ) : (
                      <p className="text-slate-500 text-xs italic text-center mt-16">Data belum tersedia.</p>
                    )}
                  </div>
                ) : (
                  <div className="flex items-center justify-center h-[260px] text-slate-500 text-xs italic">
                    {processingStatus === "transcribing" || processingStatus === "diarizing" || processingStatus === "extracting"
                      ? "AI sedang menganalisis berkas suara..."
                      : "Silakan unggah rekaman audio rapat untuk memicu notulen AI."}
                  </div>
                )}
              </div>
            </section>

            {/* Action Items */}
            <section className="bg-white border border-slate-200 shadow-sm rounded-2xl p-6">
              <h2 className="text-xs font-bold text-blue-700 uppercase tracking-wider mb-4">Action Items</h2>
              <ActionItemList
                items={actionItems}
                onToggle={handleToggleTask}
                participants={participantOptions}
                onAssign={isOrganizer ? handleAssignTask : undefined}
                onAdd={isOrganizer ? handleCreateActionItem : undefined}
              />
            </section>

          </div>
        </div>
      </div>
    </main>
  );
}
