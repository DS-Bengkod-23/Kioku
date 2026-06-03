"use client";

import React, { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Type, MapPin, Calendar, FileText, X, Plus } from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";
import { useMeeting, useUpdateMeeting } from "@/hooks/useMeeting";

export default function EditMeetingPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { data: meeting, isLoading, isError } = useMeeting(id);
  const { mutateAsync: updateMeeting, isPending } = useUpdateMeeting(id);

  const [formData, setFormData] = useState({
    title: "",
    location: "",
    dateTime: "",
    description: "",
    agenda: "",
  });
  const [participants, setParticipants] = useState<string[]>([]);
  const [emailInput, setEmailInput] = useState("");

  useEffect(() => {
    if (!meeting) return;
    const localDateTime = meeting.scheduled_at
      ? new Date(meeting.scheduled_at).toISOString().slice(0, 16)
      : "";
    setFormData({
      title: meeting.title ?? "",
      location: meeting.location ?? "",
      dateTime: localDateTime,
      description: meeting.description ?? "",
      agenda: meeting.agenda_text ?? "",
    });
    const existingEmails = (meeting.participants ?? []).map((p: any) => p.email);
    setParticipants(existingEmails);
  }, [meeting]);

  const handleAddParticipant = () => {
    const email = emailInput.trim();
    if (!email) return;
    if (!email.includes("@")) {
      toast.error("Format email tidak valid!");
      return;
    }
    if (participants.includes(email)) {
      toast.error("Email sudah ada dalam daftar!");
      return;
    }
    setParticipants((prev) => [...prev, email]);
    setEmailInput("");
  };

  const handleRemoveParticipant = (email: string) => {
    setParticipants((prev) => prev.filter((e) => e !== email));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await updateMeeting({
        title: formData.title,
        scheduled_at: new Date(formData.dateTime).toISOString(),
        location: formData.location,
        description: formData.description,
        agenda_text: formData.agenda,
        participant_emails: participants,
      });
      toast.success("Rapat berhasil diperbarui!");
      router.push(`/meetings/${id}`);
    } catch (err: any) {
      const message = err?.response?.data?.detail || "Gagal memperbarui rapat. Coba lagi.";
      toast.error(message);
    }
  };

  if (isLoading) {
    return (
      <div className="w-full min-h-screen bg-[#0A051B] flex items-center justify-center text-slate-400 text-xs font-medium">
        Memuat data rapat...
      </div>
    );
  }

  if (isError || !meeting) {
    return (
      <div className="w-full min-h-screen bg-[#0A051B] flex flex-col items-center justify-center gap-4">
        <p className="text-rose-400 text-sm">Rapat tidak ditemukan atau terjadi kesalahan.</p>
        <Link href="/meetings" className="text-purple-400 text-xs hover:underline">
          ← Kembali ke Dashboard
        </Link>
      </div>
    );
  }

  return (
    <div className="w-full min-h-screen bg-[radial-gradient(circle_at_top_left,_var(--tw-gradient-stops))] from-[#0b0a26] via-[#08061a] to-[#050412] text-white font-sans pb-16">
      <div className="absolute top-[-10%] left-[-5%] w-[900px] h-[900px] bg-[#7E61F2]/10 rounded-full blur-[150px] pointer-events-none" />

      <main className="relative z-10 max-w-3xl mx-auto px-6 pt-10 space-y-8">
        <Link
          href={`/meetings/${id}`}
          className="inline-flex items-center gap-2 text-slate-400 hover:text-white transition text-xs font-medium"
        >
          <ArrowLeft size={16} /> Kembali ke Detail Rapat
        </Link>

        <div className="space-y-1">
          <h1 className="text-2xl font-bold text-white">Edit Rapat</h1>
          <p className="text-sm text-slate-400">Perbarui informasi rapat yang sudah dijadwalkan.</p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="bg-[#120e2e]/40 border border-purple-500/10 backdrop-blur-md rounded-2xl p-8 shadow-[0_20px_50px_rgba(0,0,0,0.5)] space-y-8"
        >
          {/* SECTION 1: DETAIL RAPAT */}
          <div className="space-y-5">
            <h2 className="text-sm font-bold text-purple-400 uppercase tracking-wider border-b border-purple-950/40 pb-2">
              1. Detail Rapat
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-2">
                <label className="text-xs font-semibold text-slate-400 flex items-center gap-2">
                  <Type size={14} className="text-slate-500" /> Judul Rapat <span className="text-purple-400">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  className="w-full px-4 py-3 rounded-xl bg-[#050412]/80 border border-purple-950/50 text-slate-200 text-sm placeholder-slate-600 focus:outline-none focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/20 transition-all"
                />
              </div>

              <div className="space-y-2">
                <label className="text-xs font-semibold text-slate-400 flex items-center gap-2">
                  <MapPin size={14} className="text-slate-500" /> Lokasi / Tautan Rapat
                </label>
                <input
                  type="text"
                  value={formData.location}
                  onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                  className="w-full px-4 py-3 rounded-xl bg-[#050412]/80 border border-purple-950/50 text-slate-200 text-sm placeholder-slate-600 focus:outline-none focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/20 transition-all"
                />
              </div>

              <div className="space-y-2 md:col-span-2">
                <label className="text-xs font-semibold text-slate-400 flex items-center gap-2">
                  <Calendar size={14} className="text-slate-500" /> Jadwal & Waktu Pelaksanaan <span className="text-purple-400">*</span>
                </label>
                <input
                  type="datetime-local"
                  required
                  value={formData.dateTime}
                  onChange={(e) => setFormData({ ...formData, dateTime: e.target.value })}
                  className="w-full px-4 py-3 rounded-xl bg-[#050412]/80 border border-purple-950/50 text-slate-200 text-sm focus:outline-none focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/20 transition-all [color-scheme:dark]"
                />
              </div>
            </div>
          </div>

          {/* SECTION 2: DESKRIPSI & AGENDA */}
          <div className="space-y-5">
            <h2 className="text-sm font-bold text-purple-400 uppercase tracking-wider border-b border-purple-950/40 pb-2">
              2. Deskripsi & Agenda
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-2">
                <label className="text-xs font-semibold text-slate-400 flex items-center gap-2">
                  <FileText size={14} className="text-slate-500" /> Deskripsi Singkat
                </label>
                <textarea
                  rows={4}
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="w-full px-4 py-3 rounded-xl bg-[#050412]/80 border border-purple-950/50 text-slate-200 text-sm placeholder-slate-600 focus:outline-none focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/20 transition-all resize-none"
                />
              </div>

              <div className="space-y-2">
                <label className="text-xs font-semibold text-slate-400 flex items-center gap-2">
                  <FileText size={14} className="text-slate-500" /> Poin-Poin Agenda
                </label>
                <textarea
                  rows={4}
                  value={formData.agenda}
                  onChange={(e) => setFormData({ ...formData, agenda: e.target.value })}
                  className="w-full px-4 py-3 rounded-xl bg-[#050412]/80 border border-purple-950/50 text-slate-200 text-sm placeholder-slate-600 focus:outline-none focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/20 transition-all resize-none"
                />
              </div>
            </div>
          </div>

          {/* SECTION 3: PESERTA */}
          <div className="space-y-5">
            <h2 className="text-sm font-bold text-purple-400 uppercase tracking-wider border-b border-purple-950/40 pb-2">
              3. Daftar Peserta
            </h2>

            <div className="space-y-3">
              <label className="text-xs font-semibold text-slate-400">Tambah Peserta (Email)</label>
              <div className="flex gap-2">
                <input
                  type="email"
                  value={emailInput}
                  onChange={(e) => setEmailInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), handleAddParticipant())}
                  placeholder="Ketik email peserta..."
                  className="flex-1 px-4 py-3 rounded-xl bg-[#050412]/80 border border-purple-950/50 text-slate-200 text-sm placeholder-slate-600 focus:outline-none focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/20 transition-all"
                />
                <button
                  type="button"
                  onClick={handleAddParticipant}
                  className="px-4 rounded-xl bg-[#08061a] border border-purple-500/20 text-purple-400 hover:bg-purple-600 hover:text-white transition-all flex items-center justify-center"
                >
                  <Plus size={18} />
                </button>
              </div>
              <p className="text-[11px] text-slate-500 italic">
                * Tekan Enter atau klik tombol + untuk menambahkan. Klik × untuk menghapus peserta.
              </p>

              {participants.length > 0 && (
                <div className="flex flex-wrap gap-2 pt-2">
                  {participants.map((email) => (
                    <span
                      key={email}
                      className="flex items-center gap-2 px-3 py-1.5 bg-[#7E61F2]/10 border border-purple-500/20 text-purple-300 rounded-lg text-xs font-medium"
                    >
                      {email}
                      <button
                        type="button"
                        onClick={() => handleRemoveParticipant(email)}
                        className="text-purple-400 hover:text-rose-400 transition-colors"
                      >
                        <X size={12} />
                      </button>
                    </span>
                  ))}
                </div>
              )}

              {participants.length === 0 && (
                <p className="text-xs text-slate-600 italic">Belum ada peserta. Tambahkan email di atas.</p>
              )}
            </div>
          </div>

          {/* FOOTER ACTIONS */}
          <div className="border-t border-purple-950/40 pt-6 flex flex-col sm:flex-row items-center justify-end gap-3">
            <Link
              href={`/meetings/${id}`}
              className="w-full sm:w-auto text-center px-6 py-3 rounded-xl border border-purple-950 text-slate-400 hover:text-white hover:bg-purple-950/20 font-semibold text-sm transition-all"
            >
              Batalkan
            </Link>
            <button
              type="submit"
              disabled={isPending}
              className="w-full sm:w-auto px-8 py-3 rounded-xl bg-gradient-to-r from-[#7E61F2] to-[#6344E3] hover:from-[#8F75FA] hover:to-[#7254F5] text-white font-bold text-sm shadow-[0_4px_20px_rgba(126,97,242,0.3)] hover:shadow-[0_4px_25px_rgba(126,97,242,0.5)] transition-all duration-300 disabled:opacity-50"
            >
              {isPending ? "Menyimpan..." : "Simpan Perubahan"}
            </button>
          </div>
        </form>
      </main>
    </div>
  );
}
