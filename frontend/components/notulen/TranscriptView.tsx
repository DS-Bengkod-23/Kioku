"use client";

import React, { useState } from "react";
import { Clock, User, Search } from "lucide-react";
import { cn } from "@/lib/utils";

interface TranscriptLine {
  timestamp: string;
  speakerId: string;
  speakerName: string;
  text: string;
}

interface TranscriptViewProps {
  lines: TranscriptLine[];
}

// Helper untuk menentukan warna badge berdasarkan Speaker ID
const getSpeakerStyle = (speakerId: string) => {
  switch (speakerId) {
    case "SPEAKER_00":
      return "bg-blue-500/10 text-blue-400 border-blue-500/20";
    case "SPEAKER_01":
      return "bg-purple-500/10 text-purple-400 border-purple-500/20";
    case "SPEAKER_02":
      return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
    default:
      return "bg-slate-500/10 text-slate-400 border-slate-500/20";
  }
};

export default function TranscriptView({ lines }: TranscriptViewProps) {
  const [searchQuery, setSearchQuery] = useState("");

  // Fungsi untuk memfilter transkrip berdasarkan teks atau nama speaker
  const filteredLines = lines.filter(
    (line) =>
      line.text.toLowerCase().includes(searchQuery.toLowerCase()) ||
      line.speakerName.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-6 text-slate-200">
      {/* Bagian Atas: Judul & Search Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-white/5 pb-4">
        <h3 className="text-sm font-bold text-white">Transkrip Rapat</h3>

        {/* Search Input */}
        <div className="relative w-full sm:w-64">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            placeholder="Cari dalam transkrip..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-black/20 border border-white/10 rounded-lg pl-9 pr-4 py-1.5 text-xs text-slate-300 placeholder-slate-500 focus:outline-none focus:border-[#7E61F2]/50 transition"
          />
        </div>
      </div>

      {/* Daftar Percakapan */}
      <div className="space-y-6 max-h-[400px] overflow-y-auto pr-2 custom-scrollbar">
        {filteredLines.length > 0 ? (
          filteredLines.map((line, idx) => (
            <div key={idx} className="flex gap-4 items-start group">
              {/* Timestamp */}
              <div className="flex items-center gap-1 text-slate-500 font-mono text-[11px] pt-1 shrink-0 w-16">
                <Clock size={11} />
                {line.timestamp}
              </div>

              {/* Konten Balon / Teks Percakapan */}
              <div className="space-y-1.5 flex-1">
                {/* Badge Speaker */}
                <div className={cn(
                  "inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded border tracking-wide font-mono",
                  getSpeakerStyle(line.speakerId)
                )}>
                  <User size={10} />
                  {line.speakerName}
                </div>

                {/* Isi Teks */}
                <p className="text-xs text-slate-400 leading-relaxed font-normal group-hover:text-slate-300 transition">
                  {line.text}
                </p>
              </div>
            </div>
          ))
        ) : (
          <div className="text-center py-8 text-xs italic text-slate-500">
            Kata kunci '{searchQuery}' tidak ditemukan.
          </div>
        )}
      </div>
    </div>
  );
}