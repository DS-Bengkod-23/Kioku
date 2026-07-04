"use client";

import React from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import MeetingForm from "@/components/meetings/MeetingForm";

export default function NewMeetingPage() {
  const router = useRouter();

  return (
    <div className="w-full min-h-screen bg-slate-50 text-slate-900 font-sans relative overflow-hidden pb-16">
      <div className="relative z-10 max-w-4xl mx-auto px-6 pt-12 animate-in fade-in-0 slide-in-from-bottom-3 duration-300">
        {/* BACK NAVIGATION */}
        <button
          onClick={() => router.back()}
          className="group flex items-center gap-2 text-sm font-medium text-slate-500 hover:text-slate-900 transition-colors mb-6 outline-none"
        >
          <ArrowLeft size={16} className="group-hover:-translate-x-1 transition-transform" />
          <span>Kembali ke Dashboard</span>
        </button>

        {/* TITLE */}
        <div className="mb-10">
          <h1 className="text-3xl font-extrabold tracking-tight text-slate-900">
            Buat Rapat Baru
          </h1>
          <p className="text-sm text-slate-500 mt-1">Sistem AI akan otomatis memproses ringkasan dan transkrip setelah rapat selesai.</p>
        </div>

        {/* ISOLATED FORM COMPONENT */}
        <MeetingForm mode="create" />
      </div>
    </div>
  );
}
