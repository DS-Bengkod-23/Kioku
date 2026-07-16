"use client";

import React, { useRef } from "react";
import { UploadCloud } from "lucide-react";
import { toast } from "sonner";

interface UploadZoneProps {
  onUpload: (file: File) => void;
}

const ALLOWED_EXTENSIONS = ["mp3", "mp4", "wav", "m4a"];
// 200MB = batas atas aplikasi (lihat CLAUDE.md). Batas 25MB khusus provider OpenAI
// tetap divalidasi ulang di backend (recording.py) dengan pesan yang lebih spesifik,
// karena provider aktif bukan info yang tersedia di frontend.
const MAX_SIZE_BYTES = 200 * 1024 * 1024;

export default function UploadZone({ onUpload }: UploadZoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  // Atribut `accept` pada <input type="file"> cuma hint untuk file picker browser
  // dan sepenuhnya diabaikan oleh drag-and-drop — tanpa validasi eksplisit ini,
  // file dengan tipe/ukuran apa pun bisa mulai diupload penuh sebelum akhirnya
  // ditolak backend menit kemudian.
  const validateAndUpload = (file: File) => {
    const ext = file.name.includes(".") ? file.name.split(".").pop()!.toLowerCase() : "";
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      toast.error(`Format file .${ext || "?"} tidak didukung. Gunakan MP3, MP4, WAV, atau M4A.`);
      return;
    }
    if (file.size === 0) {
      toast.error("File kosong (0 byte). Pilih file rekaman yang valid.");
      return;
    }
    if (file.size > MAX_SIZE_BYTES) {
      toast.error(`File terlalu besar (${(file.size / 1024 / 1024).toFixed(1)}MB). Maksimum 200MB.`);
      return;
    }
    onUpload(file);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      validateAndUpload(file);
      e.target.value = "";
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (file) validateAndUpload(file);
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
        className="border-2 border-dashed border-slate-200 hover:border-indigo-400 bg-white hover:bg-indigo-50 rounded-xl p-6 text-center cursor-pointer transition-all group"
      >
        <UploadCloud size={24} className="mx-auto text-slate-500 mb-2 group-hover:text-indigo-600 transition-colors" />
        <p className="text-[11px] text-slate-700 font-medium">Klik atau drag &amp; drop rekaman</p>
        <p className="text-[10px] text-slate-500 mt-1">MP3, MP4, WAV, M4A · Maks. 200MB (25MB jika provider OpenAI)</p>
      </div>
    </>
  );
}
