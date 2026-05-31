"use client";

import React, { useState, useEffect, useMemo } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, UserCircle, Calendar, MapPin } from "lucide-react";
import Link from "next/link";
import { cn } from "@/lib/utils";

// Import komponen modular
import UploadZone from "@/components/recording/UploadZone";
import ProcessingStatus from "@/components/recording/ProcessingStatus";
import ActionItemList from "@/components/notulen/ActionItemList";
import SummaryCard from "@/components/notulen/SummaryCard";
import TranscriptView from "@/components/notulen/TranscriptView";
import AttendanceTable from "@/components/meetings/AttendanceTable";
import ParticipantList from "@/components/meetings/ParticipantList";

// Interface disamakan dengan komponen ActionItemList baru
interface ActionItem {
  id: string | number;
  task: string;
  assignee: string;
  dueDate: string; // Format YYYY-MM-DD
  status: "Aktif" | "Terlambat" | "Selesai";
  priority: "Tinggi" | "Sedang";
}

export default function MeetingDetailPage() {
  const { id } = useParams();
  const router = useRouter();

  const [activeTab, setActiveTab] = useState<"ringkasan" | "transkrip">("ringkasan");
  const [statusProses, setStatusProses] = useState<"idle" | "uploading" | "processing" | "ready">("idle");
  const [progress, setProgress] = useState(0);

  // Master State Data Rapat & Action Items
  const [currentMeeting, setCurrentMeeting] = useState<any>(null);
  const [actionItems, setActionItems] = useState<ActionItem[]>([]);

  // 1. Ambil data rapat secara dinamis dari localStorage saat halaman diload
  useEffect(() => {
    const savedMeetings = JSON.parse(localStorage.getItem("meetings") || "[]");
    const found = savedMeetings.find((m: any) => m.id === id);

    if (found) {
      setCurrentMeeting(found);

      // Jika rapat sudah punya action items bawaan AI dari localStorage, masukkan ke state
      if (found.actionItems && Array.isArray(found.actionItems)) {
        // Validasi status terlambat secara real-time berdasarkan tanggal hari ini
        const validatedItems = found.actionItems.map((item: any) => {
          if (item.status !== "Selesai") {
            const isOverdue = new Date(item.dueDate || "2026-12-31") < new Date();
            return { ...item, status: isOverdue ? "Terlambat" : "Aktif" };
          }
          return item;
        });
        setActionItems(validatedItems);
      } else {
        // Fallback default action items jika rapat baru dibuat dan belum di-upload rekaman
        setActionItems([
          { id: `${id}-1`, task: "Selesaikan integrasi API Gateway", assignee: "Jane Smith", dueDate: "2026-06-05", status: "Aktif", priority: "Tinggi" },
          { id: `${id}-2`, task: "Review dokumentasi teknis sprint 24", assignee: "John Doe", dueDate: "2026-05-28", status: "Terlambat", priority: "Sedang" }
        ]);
      }
    } else if (id === "1") {
      // Mock data fallback khusus untuk ID "1" bawaan template dashboard awal
      setCurrentMeeting({
        id: "1",
        title: "Weekly Standup Meeting - Sprint 24",
        organizer: "John Doe",
        date: "Jumat, 20 Mei 2026 pukul 16.00",
        location: "Ruang Meeting Lantai 3",
        invitedEmails: ["john.doe@company.com", "jane.doe@company.com", "mike.o@company.com"]
      });
      setActionItems([
        { id: "1-1", task: "Selesaikan responsive design", assignee: "Jane Smith", dueDate: "2026-05-20", status: "Terlambat", priority: "Tinggi" },
        { id: "1-2", task: "Setup testing automation", assignee: "John Doe", dueDate: "2026-05-25", status: "Terlambat", priority: "Tinggi" }
      ]);
    }
  }, [id]);

  // 2. Generate otomatis data presensi/kehadiran berdasarkan email undangan
  const attendanceData = useMemo(() => {
    if (!currentMeeting || !currentMeeting.invitedEmails) return [];
    return currentMeeting.invitedEmails.map((email: string) => {
      const namePart = email.split("@")[0].replace(".", " ");
      const formattedName = namePart.charAt(0).toUpperCase() + namePart.slice(1);
      return {
        name: formattedName,
        email: email,
        // Simulasi: john dan jane hadir, email lain dianggap absen demi variasi UI
        status: email.includes("john") || email.includes("jane") ? ("Hadir" as const) : ("Tidak Hadir" as const)
      };
    });
  }, [currentMeeting]);

  // Mock data hasil transkrip & ringkasan dari AI
  const meetingAiData = {
    summary: {
      executiveSummary: "Rapat membahas progress mingguan Sprint 24. Fokus utama diarahkan pada penyelesaian responsive UI dan integrasi API testing.",
      highlights: ["Frontend responsive design selesai 90%", "Automation testing terhambat library version", "API Docs perlu di-update oleh tim backend"]
    },
    transcript: [
      { timestamp: "00:00.0", speakerId: "SPEAKER_00", speakerName: "John Doe", text: "Selamat pagi semuanya, mari kita mulai standup meeting sprint 24 hari ini." },
      { timestamp: "00:14.5", speakerId: "SPEAKER_01", speakerName: "Jane Smith", text: "Untuk update frontend responsive design sisa halaman dashboard utama saja yang perlu sentuhan akhir." }
    ]
  };

  // 3. Simulasi progress uploading rekaman suara
  const handleSimulateUpload = () => {
    setStatusProses("uploading");
    let p = 0;
    const interval = setInterval(() => {
      p += 20;
      setProgress(p);
      if (p >= 100) {
        clearInterval(interval);
        setStatusProses("processing");
        setTimeout(() => {
          setStatusProses("ready");

          // Ikut simpan action items ke dalam database lokal rapat ini agar tersinkron permanen
          if (currentMeeting) {
            const savedMeetings = JSON.parse(localStorage.getItem("meetings") || "[]");
            const updatedMeetings = savedMeetings.map((m: any) => {
              if (m.id === currentMeeting.id) {
                return { ...m, actionItems: actionItems };
              }
              return m;
            });
            localStorage.setItem("meetings", JSON.stringify(updatedMeetings));
          }
        }, 1500);
      }
    }, 300);
  };

  // 4. Toggle status checkbox tugas (Aktif <-> Selesai) dan simpan permanen ke localStorage
  const handleToggleTask = (taskId: string | number) => {
    const updatedItems = actionItems.map(item => {
      if (item.id !== taskId) return item;
      if (item.status === "Selesai") {
        const isOverdue = new Date(item.dueDate) < new Date();
        return { ...item, status: isOverdue ? ("Terlambat" as const) : ("Aktif" as const) };
      }
      return { ...item, status: "Selesai" as const };
    });

    setActionItems(updatedItems);

    // Update balik ke master data meetings di localStorage agar halaman "Tugas Saya" ikut berubah
    if (currentMeeting) {
      const savedMeetings = JSON.parse(localStorage.getItem("meetings") || "[]");
      const updatedMeetings = savedMeetings.map((m: any) => {
        if (m.id === currentMeeting.id) {
          return { ...m, actionItems: updatedItems };
        }
        return m;
      });
      localStorage.setItem("meetings", JSON.stringify(updatedMeetings));
    }
  };

  // State loading pelindung sebelum data ditarik dari localStorage
  if (!currentMeeting) {
    return (
      <div className="w-full min-h-screen bg-[#0A051B] flex items-center justify-center text-slate-400 text-xs font-medium">
        Memuat detail data rapat...
      </div>
    );
  }

  return (
    <main className="bg-[#0A051B] min-h-screen text-slate-200 pb-16 px-6">
      <div className="max-w-7xl mx-auto pt-8">

        {/* Tombol Kembali */}
        <Link href="/meetings" className="inline-flex items-center gap-2 text-slate-400 hover:text-white transition text-xs font-medium mb-6">
          <ArrowLeft size={16} /> Kembali ke Dashboard
        </Link>

        {/* Judul Rapat Utama */}
        <h1 className="text-2xl font-bold text-white mb-8">{currentMeeting.title}</h1>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

          {/* ================= KOLOM KIRI (DATA & ADMINISTRASI) ================= */}
          <div className="space-y-6">

            {/* 1. Box Upload Rekaman */}
            <section className="bg-[#110A31]/70 border border-white/5 p-6 rounded-2xl">
              <h2 className="text-xs font-bold text-slate-400 uppercase mb-4 tracking-wider">Upload Rekaman</h2>
              {statusProses === "idle" ? (
                <UploadZone onUpload={handleSimulateUpload} />
              ) : (
                <ProcessingStatus status={statusProses} progress={progress} />
              )}
            </section>

            {/* 2. Box Informasi Metadata Rapat */}
            <section className="bg-[#110A31]/70 border border-white/5 p-6 rounded-2xl space-y-4">
              <h2 className="text-xs font-bold text-slate-400 uppercase tracking-wider border-b border-white/5 pb-3">Informasi Rapat</h2>
              <div className="text-xs space-y-3.5 text-slate-300">
                <p className="flex items-center gap-2.5"><UserCircle className="text-purple-400" size={15} /> {currentMeeting.organizer || "John Doe"}</p>
                <p className="flex items-center gap-2.5"><Calendar className="text-purple-400" size={15} /> {currentMeeting.date}</p>
                <p className="flex items-center gap-2.5"><MapPin className="text-purple-400" size={15} /> {currentMeeting.location || "Online Meeting"}</p>
              </div>
            </section>

            {/* 3. Box Daftar Undangan Email */}
            <section className="bg-[#110A31]/70 border border-white/5 p-6 rounded-2xl">
              <ParticipantList emails={currentMeeting.invitedEmails || []} />
            </section>

            {/* 4. Box Status Kehadiran (Tanpa Kolom Jam Masuk) */}
            <section className="bg-[#110A31]/70 border border-white/5 p-6 rounded-2xl">
              <AttendanceTable participants={attendanceData} />
            </section>
          </div>

          {/* ================= KOLOM KANAN (PROSES AI & OUTPUT TUGAS) ================= */}
          <div className="lg:col-span-2 space-y-6">

            {/* 1. Box Hasil Pemrosesan AI (Tabs Ringkasan / Transkrip) */}
            <section className="bg-[#110A31]/70 border border-white/5 rounded-2xl overflow-hidden">
              <div className="flex p-1 bg-black/20 border-b border-white/5">
                <button
                  onClick={() => setActiveTab("ringkasan")}
                  className={cn("flex-1 py-2.5 text-xs font-bold rounded-xl transition", activeTab === "ringkasan" ? "bg-[#7E61F2] text-white" : "text-slate-400 hover:text-slate-200")}
                >
                  Ringkasan AI
                </button>
                <button
                  onClick={() => setActiveTab("transkrip")}
                  className={cn("flex-1 py-2.5 text-xs font-bold rounded-xl transition", activeTab === "transkrip" ? "bg-[#7E61F2] text-white" : "text-slate-400 hover:text-slate-200")}
                >
                  Transkrip Audio
                </button>
              </div>
              <div className="p-6 min-h-[320px]">
                {statusProses === "ready" ? (
                  <div className="animate-in fade-in duration-300">
                    {activeTab === "ringkasan" ? (
                      <SummaryCard summary={meetingAiData.summary} />
                    ) : (
                      <TranscriptView lines={meetingAiData.transcript} />
                    )}
                  </div>
                ) : (
                  <div className="flex items-center justify-center h-[260px] text-slate-500 text-xs italic">
                    {statusProses === "processing" ? "AI sedang menganalisis berkas suara..." : "Silakan unggah rekaman audio rapat untuk memicu notulen AI."}
                  </div>
                )}
              </div>
            </section>

            {/* 2. Box Daftar Action Items */}
            <section className="bg-[#110A31]/70 border border-white/5 p-6 rounded-2xl">
              <h2 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-4 flex items-center gap-2">
                Action Items
              </h2>
              <ActionItemList items={actionItems} onToggle={handleToggleTask} />
            </section>

          </div>
        </div>
      </div>
    </main>
  );
}