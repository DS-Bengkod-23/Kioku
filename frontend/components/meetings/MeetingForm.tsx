"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { X, Plus, Type, MapPin, Calendar, FileText, Clock } from "lucide-react";
import { toast } from "sonner";
import { useCreateMeeting } from "@/hooks/useMeetings";
import { useUpdateMeeting } from "@/hooks/useMeeting";
import { FormError } from "@/components/ui/form-error";
import { extractApiError } from "@/lib/utils";

export interface MeetingFormInitialData {
  title: string;
  location: string;
  locationBuilding?: string;
  locationRoom?: string;
  locationCity?: string;
  dateTime: string;
  description: string;
  agenda: string;
  durationHours: number;
  durationMins: number;
  participants: string[];
}

interface MeetingFormProps {
  mode?: "create" | "edit";
  meetingId?: string;
  initialData?: MeetingFormInitialData;
}

export default function MeetingForm({ mode = "create", meetingId, initialData }: MeetingFormProps) {
  const router = useRouter();
  const { mutateAsync: createMeeting, isPending: isCreating } = useCreateMeeting();
  const { mutateAsync: updateMeeting, isPending: isUpdating } = useUpdateMeeting(meetingId ?? "");
  const isPending = mode === "create" ? isCreating : isUpdating;

  const [formError, setFormError] = useState<string | null>(null);
  const [formData, setFormData] = useState({
    title: initialData?.title ?? "",
    location: initialData?.location ?? "",
    locationBuilding: initialData?.locationBuilding ?? "",
    locationRoom: initialData?.locationRoom ?? "",
    locationCity: initialData?.locationCity ?? "",
    dateTime: initialData?.dateTime ?? "",
    description: initialData?.description ?? "",
    agenda: initialData?.agenda ?? "",
    durationHours: initialData?.durationHours ?? 1,
    durationMins: initialData?.durationMins ?? 0,
  });
  const [emailInput, setEmailInput] = useState("");
  const [participants, setParticipants] = useState<string[]>(initialData?.participants ?? []);

  const handleAddParticipant = () => {
    const email = emailInput.trim();
    if (!email) return;
    if (!email.includes("@")) {
      toast.error("Format email tidak valid!");
      return;
    }
    if (participants.includes(email)) {
      toast.error("Email sudah ditambahkan!");
      return;
    }
    setParticipants([...participants, email]);
    setEmailInput("");
  };

  const handleRemoveParticipant = (email: string) => {
    setParticipants(participants.filter((p) => p !== email));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    const totalMinutes = formData.durationHours * 60 + formData.durationMins;
    if (totalMinutes === 0) {
      setFormError("Durasi rapat tidak boleh 0 menit.");
      return;
    }

    const payload = {
      title: formData.title,
      scheduled_at: new Date(formData.dateTime).toISOString(),
      location: formData.location,
      location_building: formData.locationBuilding || undefined,
      location_room: formData.locationRoom || undefined,
      location_city: formData.locationCity || undefined,
      description: formData.description,
      agenda_text: formData.agenda,
      participant_emails: participants,
      duration_minutes: totalMinutes,
    };

    try {
      if (mode === "create") {
        const result = await createMeeting(payload);
        toast.success("Rapat berhasil dijadwalkan!");
        router.push(`/meetings/${result.id}`);
      } else {
        await updateMeeting(payload);
        toast.success("Rapat berhasil diperbarui!");
        router.push(`/meetings/${meetingId}`);
      }
    } catch (err: any) {
      setFormError(
        extractApiError(
          err,
          mode === "create" ? "Gagal membuat rapat. Coba lagi." : "Gagal memperbarui rapat. Coba lagi."
        )
      );
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="bg-white border border-slate-200 shadow-sm rounded-2xl p-8 space-y-8"
    >
      {/* SECTION 1: INFORMASI UTAMA */}
      <div className="space-y-5">
        <h2 className="text-sm font-bold text-slate-500 uppercase tracking-wider border-b border-slate-200 pb-2">
          1. Detail Rapat
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-2">
            <label className="text-xs font-semibold text-slate-700 flex items-center gap-2">
              <Type size={14} className="text-slate-500" /> Judul Rapat <span className="text-blue-600">*</span>
            </label>
            <input
              type="text"
              required
              placeholder="Contoh: Weekly Standup Sprint"
              value={formData.title}
              className="w-full px-4 py-3 rounded-xl bg-white border border-slate-300 text-slate-900 text-sm placeholder-slate-400 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/20 transition-all"
              onChange={(e) => setFormData({ ...formData, title: e.target.value })}
            />
          </div>

          <div className="space-y-2">
            <label className="text-xs font-semibold text-slate-700 flex items-center gap-2">
              <MapPin size={14} className="text-slate-500" /> Lokasi / Tautan Rapat <span className="text-blue-600">*</span>
            </label>
            <input
              type="text"
              required
              placeholder="Contoh: Zoom / Ruang Rapat Lt. 3"
              value={formData.location}
              className="w-full px-4 py-3 rounded-xl bg-white border border-slate-300 text-slate-900 text-sm placeholder-slate-400 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/20 transition-all"
              onChange={(e) => setFormData({ ...formData, location: e.target.value })}
            />
          </div>

          <div className="space-y-2">
            <label className="text-xs font-semibold text-slate-700 flex items-center gap-2">
              <Calendar size={14} className="text-slate-500" /> Jadwal & Waktu Pelaksanaan <span className="text-blue-600">*</span>
            </label>
            <input
              type="datetime-local"
              required
              value={formData.dateTime}
              className="w-full px-4 py-3 rounded-xl bg-white border border-slate-300 text-slate-900 text-sm focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/20 transition-all [color-scheme:light]"
              onChange={(e) => setFormData({ ...formData, dateTime: e.target.value })}
            />
          </div>

          <div className="space-y-2">
            <label className="text-xs font-semibold text-slate-700 flex items-center gap-2">
              <Clock size={14} className="text-slate-500" /> Durasi Rapat <span className="text-blue-600">*</span>
            </label>
            <div className="flex gap-2">
              <select
                value={formData.durationHours}
                onChange={(e) => setFormData({ ...formData, durationHours: Number(e.target.value) })}
                className="flex-1 px-4 py-3 rounded-xl bg-white border border-slate-300 text-slate-900 text-sm focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/20 transition-all"
              >
                {[0, 1, 2, 3, 4].map((h) => (
                  <option key={h} value={h}>{h} jam</option>
                ))}
              </select>
              <select
                value={formData.durationMins}
                onChange={(e) => setFormData({ ...formData, durationMins: Number(e.target.value) })}
                className="flex-1 px-4 py-3 rounded-xl bg-white border border-slate-300 text-slate-900 text-sm focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/20 transition-all"
              >
                {[0, 15, 30, 45].map((m) => (
                  <option key={m} value={m}>{m} menit</option>
                ))}
              </select>
            </div>
          </div>
        </div>

        <div className="space-y-2 pt-2">
          <p className="text-[11px] text-slate-500 italic">
            Opsional — dipakai untuk detail lokasi di PDF notulen resmi.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="space-y-2">
              <label className="text-xs font-semibold text-slate-700 flex items-center gap-2">
                <MapPin size={14} className="text-slate-500" /> Gedung
              </label>
              <input
                type="text"
                placeholder="Contoh: Gedung G Lantai 1"
                value={formData.locationBuilding}
                className="w-full px-4 py-3 rounded-xl bg-white border border-slate-300 text-slate-900 text-sm placeholder-slate-400 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/20 transition-all"
                onChange={(e) => setFormData({ ...formData, locationBuilding: e.target.value })}
              />
            </div>

            <div className="space-y-2">
              <label className="text-xs font-semibold text-slate-700 flex items-center gap-2">
                <MapPin size={14} className="text-slate-500" /> Ruang
              </label>
              <input
                type="text"
                placeholder="Contoh: Rapat G1"
                value={formData.locationRoom}
                className="w-full px-4 py-3 rounded-xl bg-white border border-slate-300 text-slate-900 text-sm placeholder-slate-400 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/20 transition-all"
                onChange={(e) => setFormData({ ...formData, locationRoom: e.target.value })}
              />
            </div>

            <div className="space-y-2">
              <label className="text-xs font-semibold text-slate-700 flex items-center gap-2">
                <MapPin size={14} className="text-slate-500" /> Kabupaten/Kota
              </label>
              <input
                type="text"
                placeholder="Contoh: Semarang"
                value={formData.locationCity}
                className="w-full px-4 py-3 rounded-xl bg-white border border-slate-300 text-slate-900 text-sm placeholder-slate-400 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/20 transition-all"
                onChange={(e) => setFormData({ ...formData, locationCity: e.target.value })}
              />
            </div>
          </div>
        </div>
      </div>

      {/* SECTION 2: KONTEN & AGENDA */}
      <div className="space-y-5">
        <h2 className="text-sm font-bold text-slate-500 uppercase tracking-wider border-b border-slate-200 pb-2">
          2. Deskripsi & Agenda
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-2">
            <label className="text-xs font-semibold text-slate-700 flex items-center gap-2">
              <FileText size={14} className="text-slate-500" /> Deskripsi Singkat
            </label>
            <textarea
              rows={4}
              placeholder="Berikan gambaran ringkas mengenai topik rapat utama..."
              value={formData.description}
              className="w-full px-4 py-3 rounded-xl bg-white border border-slate-300 text-slate-900 text-sm placeholder-slate-400 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/20 transition-all resize-none"
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            />
          </div>

          <div className="space-y-2">
            <label className="text-xs font-semibold text-slate-700 flex items-center gap-2">
              <FileText size={14} className="text-slate-500" /> Poin-Poin Agenda
            </label>
            <textarea
              rows={4}
              placeholder="1. Pembuka&#10;2. Pembahasan Sprint 24&#10;3. Evaluasi Kendala"
              value={formData.agenda}
              className="w-full px-4 py-3 rounded-xl bg-white border border-slate-300 text-slate-900 text-sm placeholder-slate-400 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/20 transition-all resize-none"
              onChange={(e) => setFormData({ ...formData, agenda: e.target.value })}
            />
          </div>
        </div>
      </div>

      {/* SECTION 3: PESERTA */}
      <div className="space-y-5">
        <h2 className="text-sm font-bold text-slate-500 uppercase tracking-wider border-b border-slate-200 pb-2">
          3. Distribusi Undangan
        </h2>

        <div className="space-y-3">
          <label className="text-xs font-semibold text-slate-700">Undang Peserta Rapat (Email)</label>
          <div className="flex gap-2">
            <input
              type="email"
              value={emailInput}
              onChange={(e) => setEmailInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), handleAddParticipant())}
              placeholder="Ketik email rekan tim kamu di sini..."
              className="flex-1 px-4 py-3 rounded-xl bg-white border border-slate-300 text-slate-900 text-sm placeholder-slate-400 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/20 transition-all"
            />
            <button
              type="button"
              onClick={handleAddParticipant}
              className="px-4 rounded-xl bg-white border border-slate-200 text-blue-600 hover:bg-blue-700 hover:text-white transition-all flex items-center justify-center outline-none"
            >
              <Plus size={18} />
            </button>
          </div>
          <p className="text-[11px] text-slate-500 italic">
            * Tekan Enter atau klik tombol + untuk memasukkan email ke dalam list undangan.
          </p>

          {participants.length > 0 && (
            <div className="flex flex-wrap gap-2 pt-2">
              {participants.map((email) => (
                <span
                  key={email}
                  className="flex items-center gap-2 px-3 py-1.5 bg-blue-50 border border-slate-200 text-blue-700 rounded-lg text-xs font-medium"
                >
                  <span>{email}</span>
                  <X
                    size={12}
                    className="cursor-pointer text-blue-600 hover:text-red-400 transition-colors"
                    onClick={() => handleRemoveParticipant(email)}
                  />
                </span>
              ))}
            </div>
          )}
        </div>
      </div>

      <FormError message={formError} />

      {/* FOOTER ACTIONS BUTTON */}
      <div className="border-t border-slate-200 pt-6 flex flex-col sm:flex-row items-center justify-end gap-3">
        {mode === "edit" && meetingId ? (
          <Link
            href={`/meetings/${meetingId}`}
            className="w-full sm:w-auto text-center px-6 py-3 rounded-xl border border-slate-200 text-slate-700 hover:text-slate-900 hover:bg-slate-50 font-semibold text-sm transition-all"
          >
            Batalkan
          </Link>
        ) : (
          <button
            type="button"
            onClick={() => router.back()}
            className="w-full sm:w-auto px-6 py-3 rounded-xl border border-slate-200 text-slate-700 hover:text-slate-900 hover:bg-slate-50 font-semibold text-sm transition-all"
          >
            Batalkan
          </button>
        )}
        <button
          type="submit"
          disabled={isPending}
          className="w-full sm:w-auto px-8 py-3 rounded-xl bg-blue-700 hover:bg-blue-800 text-white font-bold text-sm transition-all duration-300 disabled:opacity-50"
        >
          {isPending ? "Menyimpan..." : mode === "create" ? "Jadwalkan Pertemuan" : "Simpan Perubahan"}
        </button>
      </div>
    </form>
  );
}
