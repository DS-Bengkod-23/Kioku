"use client";

import React from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { useMeeting } from "@/hooks/useMeeting";
import MeetingForm from "@/components/meetings/MeetingForm";
import type { ParticipantResponse } from "@/types";

export default function EditMeetingPage() {
  const { id } = useParams<{ id: string }>();
  const { data: meeting, isLoading, isError } = useMeeting(id);

  if (isLoading) {
    return (
      <div className="w-full min-h-screen bg-slate-50 flex items-center justify-center text-slate-500 text-xs font-medium">
        Memuat data rapat...
      </div>
    );
  }

  if (isError || !meeting) {
    return (
      <div className="w-full min-h-screen bg-slate-50 flex flex-col items-center justify-center gap-4">
        <p className="text-rose-400 text-sm">Rapat tidak ditemukan atau terjadi kesalahan.</p>
        <Link href="/meetings" className="text-blue-600 text-xs hover:underline">
        Kembali ke Dashboard
        </Link>
      </div>
    );
  }

  const localDateTime = meeting.scheduled_at
    ? new Date(meeting.scheduled_at).toISOString().slice(0, 16)
    : "";
  const existingEmails = (meeting.participants ?? [])
    .filter((p: ParticipantResponse) => p.role !== "organizer")
    .map((p: ParticipantResponse) => p.email);

  return (
    <div className="w-full min-h-screen bg-slate-50 text-slate-900 font-sans pb-16">
      <main className="relative z-10 max-w-3xl mx-auto px-6 pt-10 space-y-8">
        <Link
          href={`/meetings/${id}`}
          className="inline-flex items-center gap-2 text-slate-500 hover:text-slate-900 transition text-xs font-medium"
        >
          <ArrowLeft size={16} /> Kembali ke Detail Rapat
        </Link>

        <div className="space-y-1">
          <h1 className="text-2xl font-bold text-slate-900">Edit Rapat</h1>
          <p className="text-sm text-slate-500">Perbarui informasi rapat yang sudah dijadwalkan.</p>
        </div>

        <MeetingForm
          mode="edit"
          meetingId={id}
          initialData={{
            title: meeting.title ?? "",
            location: meeting.location ?? "",
            dateTime: localDateTime,
            description: meeting.description ?? "",
            agenda: meeting.agenda_text ?? "",
            durationHours: Math.floor((meeting.duration_minutes ?? 60) / 60),
            durationMins: (meeting.duration_minutes ?? 60) % 60,
            participants: existingEmails,
          }}
        />
      </main>
    </div>
  );
}
