import { CheckCircle2, FileAudio } from "lucide-react";

interface Props {
  status: "idle" | "uploading" | "processing" | "ready";
  progress: number;
  fileName?: string | null;
}

export default function ProcessingStatus({ status, progress, fileName }: Props) {
  if (status === "uploading") {
    return (
      <div className="space-y-2">
        <div className="w-full bg-slate-200 h-2 rounded-full overflow-hidden">
          <div className="bg-indigo-600 h-full transition-all duration-300" style={{ width: `${progress}%` }} />
        </div>
        <p className="text-[10px] text-slate-500">
          {fileName ? `Mengunggah ${fileName}...` : "Mengunggah..."} {progress}%
        </p>
      </div>
    );
  }

  if (status === "processing") {
    return (
      <div className="space-y-2">
        {fileName && (
          <div className="flex items-center gap-2 text-xs text-slate-700 font-medium">
            <FileAudio size={14} className="text-indigo-600" /> {fileName}
          </div>
        )}
        <p className="text-[10px] text-slate-500">AI sedang memproses...</p>
      </div>
    );
  }

  if (status === "ready") {
    return (
      <div className="bg-emerald-50 border border-emerald-200 p-4 rounded-xl flex items-center gap-2 text-emerald-700 text-xs font-bold">
        <CheckCircle2 size={16} /> {fileName || "File Siap"}
      </div>
    );
  }

  return null;
}
