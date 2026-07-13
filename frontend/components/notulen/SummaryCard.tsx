"use client";

import React from "react";
import { FileText, Sparkles, CheckCircle2, Tag } from "lucide-react";

interface SummaryData {
  executiveSummary: string;
  highlights: string[];
  topics?: string[];
}

interface SummaryCardProps {
  summary: SummaryData;
}

export default function SummaryCard({ summary }: SummaryCardProps) {
  return (
    <div className="space-y-6 text-slate-700">
      {/* Header */}
      <div className="flex items-center gap-2 border-b border-slate-200 pb-4">
        <Sparkles size={16} className="text-indigo-600" />
        <h3 className="text-sm font-bold text-slate-900">Ringkasan Otomatis AI</h3>
      </div>

      {/* Topics / Topik Dibahas */}
      {summary.topics && summary.topics.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
            <Tag size={12} /> Topik yang Dibahas
          </h4>
          <div className="flex flex-wrap gap-2">
            {summary.topics.map((topic, i) => (
              <span
                key={i}
                className="text-[11px] px-2.5 py-1 rounded-full bg-indigo-50 border border-slate-200 text-indigo-700 font-medium"
              >
                {topic}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Ringkasan Eksekutif */}
      <div className="space-y-2">
        <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
          <FileText size={12} /> Ringkasan Eksekutif
        </h4>
        <p className="text-xs leading-relaxed text-slate-700 bg-slate-50 p-4 rounded-xl border border-slate-200">
          {summary.executiveSummary}
        </p>
      </div>

      {/* Keputusan / Highlights */}
      {summary.highlights && summary.highlights.length > 0 && (
        <div className="space-y-3">
          <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider">
            Keputusan Rapat
          </h4>
          <div className="grid gap-2.5">
            {summary.highlights.map((point, index) => (
              <div
                key={index}
                className="flex items-start gap-3 p-3 bg-slate-50 rounded-xl border border-slate-200 hover:bg-slate-100 transition duration-200"
              >
                <CheckCircle2 size={14} className="text-emerald-400 mt-0.5 shrink-0" />
                <p className="text-xs text-slate-700 leading-normal">{point}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
