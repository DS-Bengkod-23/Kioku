"use client";

import { useEffect, useState } from "react";
import { Play, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { getRecordingAudioBlobUrl } from "@/lib/api";
import { extractApiError } from "@/lib/utils";

interface AudioPlayerProps {
  meetingId: string;
}

// Lazy-load: rekaman bisa sampai 200MB (lihat CLAUDE.md), jadi jangan langsung
// di-download begitu halaman dibuka — tunggu user eksplisit klik dulu.
export default function AudioPlayer({ meetingId }: AudioPlayerProps) {
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    return () => {
      if (audioUrl) URL.revokeObjectURL(audioUrl);
    };
  }, [audioUrl]);

  const handleLoad = async () => {
    setIsLoading(true);
    try {
      const url = await getRecordingAudioBlobUrl(meetingId);
      setAudioUrl(url);
    } catch (err) {
      toast.error(extractApiError(err, "Gagal memuat rekaman audio."));
    } finally {
      setIsLoading(false);
    }
  };

  if (audioUrl) {
    return <audio controls src={audioUrl} className="w-full h-10" />;
  }

  return (
    <button
      onClick={handleLoad}
      disabled={isLoading}
      className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl border border-slate-200 text-slate-600 text-xs font-semibold hover:border-indigo-300 hover:text-indigo-700 transition disabled:opacity-60"
    >
      {isLoading ? (
        <><Loader2 size={14} className="animate-spin" /> Memuat rekaman...</>
      ) : (
        <><Play size={14} /> Putar Rekaman Asli</>
      )}
    </button>
  );
}
