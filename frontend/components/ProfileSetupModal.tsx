"use client";

import { useState } from "react";
import { X } from "lucide-react";
import { toast } from "sonner";
import { useUpdateProfile } from "@/hooks/useProfile";

interface ProfileSetupModalProps {
  onClose: () => void;
}

export default function ProfileSetupModal({ onClose }: ProfileSetupModalProps) {
  const { mutate: updateProfile, isPending } = useUpdateProfile();
  const [form, setForm] = useState({ job_title: "", department: "", bio: "" });

  const handleSave = () => {
    updateProfile(form, {
      onSuccess: () => {
        toast.success("Profil berhasil dilengkapi!");
        onClose();
      },
      onError: () => toast.error("Gagal menyimpan profil. Coba lagi."),
    });
  };

  return (
    <div className="fixed inset-0 z-[100] bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-xl p-6 relative animate-in fade-in-0 zoom-in-95 duration-200">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-slate-400 hover:text-slate-700 transition"
          title="Tutup, isi nanti aja"
        >
          <X size={18} />
        </button>

        <h2 className="text-lg font-bold text-slate-900">Lengkapi Profil Kamu</h2>
        <p className="text-xs text-slate-500 mt-1 mb-5">Biar tim lain gampang kenalin kamu pas rapat.</p>

        <div className="space-y-4">
          <div className="space-y-1.5">
            <label className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Jabatan</label>
            <input
              value={form.job_title}
              onChange={(e) => setForm((f) => ({ ...f, job_title: e.target.value }))}
              placeholder="misal: Product Manager"
              className="w-full bg-white border border-slate-300 rounded-xl py-2.5 px-4 outline-none text-sm text-slate-900 placeholder-slate-400 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/20 transition"
            />
          </div>
          <div className="space-y-1.5">
            <label className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Departemen</label>
            <input
              value={form.department}
              onChange={(e) => setForm((f) => ({ ...f, department: e.target.value }))}
              placeholder="misal: Engineering"
              className="w-full bg-white border border-slate-300 rounded-xl py-2.5 px-4 outline-none text-sm text-slate-900 placeholder-slate-400 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/20 transition"
            />
          </div>
          <div className="space-y-1.5">
            <label className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Bio Singkat</label>
            <textarea
              rows={2}
              value={form.bio}
              onChange={(e) => setForm((f) => ({ ...f, bio: e.target.value }))}
              placeholder="Ceritakan sedikit tentang kamu..."
              className="w-full bg-white border border-slate-300 rounded-xl py-2.5 px-4 outline-none text-sm text-slate-900 placeholder-slate-400 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/20 transition resize-none"
            />
          </div>
        </div>

        <div className="flex gap-3 mt-6">
          <button
            onClick={onClose}
            className="flex-1 py-2.5 rounded-xl text-xs font-bold text-slate-500 hover:bg-slate-100 border border-slate-200 transition"
          >
            Nanti Saja
          </button>
          <button
            onClick={handleSave}
            disabled={isPending}
            className="flex-1 py-2.5 rounded-xl text-xs font-bold bg-indigo-600 text-white hover:bg-indigo-700 transition disabled:opacity-60"
          >
            {isPending ? "Menyimpan..." : "Simpan"}
          </button>
        </div>
      </div>
    </div>
  );
}
