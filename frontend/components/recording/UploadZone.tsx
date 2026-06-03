"use client";

import React, { useRef } from "react";
import { UploadCloud } from "lucide-react";

interface UploadZoneProps {
  onUpload: (file: File) => void;
}

export default function UploadZone({ onUpload }: UploadZoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      onUpload(file);
      e.target.value = "";
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (file) onUpload(file);
  };

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        accept=".mp3,.mp4,.wav,.m4a,audio/*"
        className="hidden"
        onChange={handleFileChange}
      />
      <div
        onClick={() => inputRef.current?.click()}
        onDrop={handleDrop}
        onDragOver={(e) => e.preventDefault()}
        className="border-2 border-dashed border-white/10 hover:border-[#7E61F2]/50 bg-white/[0.02] hover:bg-[#7E61F2]/5 rounded-xl p-6 text-center cursor-pointer transition-all group"
      >
        <UploadCloud size={24} className="mx-auto text-slate-500 mb-2 group-hover:text-purple-400 transition-colors" />
        <p className="text-[11px] text-slate-400 font-medium">Klik atau drag &amp; drop rekaman</p>
        <p className="text-[10px] text-slate-600 mt-1">MP3, MP4, WAV, M4A · Maks. 200MB</p>
      </div>
    </>
  );
}
