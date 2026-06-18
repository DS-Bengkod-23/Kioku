"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Eye, EyeOff, Sparkles, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import { FormError } from "@/components/ui/form-error";
import { extractApiError } from "@/lib/utils";

export default function LoginPage() {
  const router = useRouter();
  const [formData, setFormData] = useState({ email: "", password: "" });
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isFlying, setIsFlying] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setFormError(null);

    try {
      const data = await import("@/lib/api").then(m => m.loginUser(formData));

      const userSession = {
        name: data.name || formData.email.split("@")[0],
        email: formData.email,
        role: "Team Member",
        department: "Product Development",
        joinDate: new Date().toLocaleDateString("id-ID", { month: "long", year: "numeric" }),
        bio: "",
      };
      localStorage.setItem("user_profile", JSON.stringify(userSession));
      window.dispatchEvent(new Event("profileUpdate"));

      toast.success("Login berhasil! Menyiapkan dashboard Anda...");
      setTimeout(() => {
        setIsFlying(true);
        setTimeout(() => router.replace("/meetings"), 1000);
      }, 600);
    } catch (err: any) {
      setFormError(extractApiError(err, "Email atau password salah."));
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen bg-slate-50 text-slate-900 font-sans overflow-hidden relative items-center justify-center">

      {/* MAIN CONTAINER */}
      <div className="w-full max-w-6xl mx-auto px-6 grid lg:grid-cols-12 gap-12 items-center relative z-10">

        {/* TATA LETAK KIRI: Branding & Copywriting (Komposisi 5 Kolom) */}
        <div className="hidden lg:flex lg:col-span-5 flex-col space-y-8 text-left">
          <div className="flex items-center gap-3">
            <div className="h-6 w-6 rounded-lg bg-gradient-to-tr from-blue-800 to-blue-600 flex items-center justify-center">
              <div className="h-2 w-2 rounded-full bg-white animate-ping" />
            </div>
            <span className="font-bold text-base tracking-widest text-slate-900">MEETMATE</span>
          </div>

          <div className="space-y-4">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-slate-200 bg-blue-50 text-xs text-blue-600 font-medium">
              <Sparkles size={12} /> Powered by Advanced AI Insights
            </div>
            <h1 className="text-4xl xl:text-5xl font-black tracking-tight leading-[1.15] text-slate-900">
              Selamat Datang <br />
              <span className="text-blue-700">
                Kembali.
              </span>
            </h1>
            <p className="text-sm text-slate-500 leading-relaxed max-w-sm">
              Masuk kembali untuk mengakses semua transkrip rapat otomatis, ringkasan berbasis AI, dan poin tugas penting Anda.
            </p>
          </div>

          <div className="pt-4">
            <div className="w-full max-w-[280px] p-4 rounded-2xl border border-slate-200 bg-white shadow-lg flex items-center gap-4">
              <div className="p-3 rounded-xl bg-blue-50 text-blue-700">
                <ShieldCheck size={24} />
              </div>
              <div>
                <h4 className="text-xs font-bold text-slate-900">Keamanan Terjamin</h4>
                <p className="text-[11px] text-slate-500 mt-0.5">Enkripsi end-to-end data rapat</p>
              </div>
            </div>
          </div>
          <div className="text-[11px] text-slate-500">&copy; {new Date().getFullYear()} MeetMate. All rights reserved.</div>
        </div>

        {/* BAGIAN KANAN: Form Wrapper */}
        <div className="w-full lg:col-span-7 flex items-center justify-center p-6 lg:p-12 relative z-10">
          <div
            className={`w-full max-w-md bg-white rounded-3xl shadow-lg border border-slate-200 p-8 md:p-10
            transition-all duration-1000 ease-in-out transform
            ${isFlying ? "opacity-0 -translate-y-[100vh] scale-75 rotate-12 blur-sm pointer-events-none" : "opacity-100 translate-y-0 scale-100"}`}
          >
            <div className="mb-8">
              <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Masuk ke Akun Anda</h2>
              <p className="text-xs text-slate-500 mt-1.5">Silakan masukkan kredensial terdaftar untuk melanjutkan</p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-5">
              <div className="space-y-2">
                <label className="block text-[11px] font-bold text-slate-500 uppercase tracking-widest">Email Address</label>
                <input
                  type="email"
                  name="email"
                  placeholder="name@example.com"
                  value={formData.email}
                  onChange={handleChange}
                  className="w-full px-4 py-3 rounded-xl border border-slate-300 bg-white text-sm text-slate-900 placeholder-slate-400 focus:border-blue-500 focus:outline-none transition-all focus:ring-1 focus:ring-blue-500/20"
                  required
                />
              </div>

              <div>
                <div className="flex justify-between items-center mb-2">
                  <label className="block text-[11px] font-bold text-slate-500 uppercase tracking-widest">Password</label>
                  <Link href="/forgot-password" className="text-[11px] font-semibold text-slate-500 hover:text-blue-600 hover:underline transition-colors">Lupa Password?</Link>
                </div>
                <div className="relative">
                  <input
                    type={showPassword ? "text" : "password"}
                    name="password"
                    placeholder="••••••••"
                    value={formData.password}
                    onChange={handleChange}
                    className="w-full px-4 py-3 pr-10 rounded-xl border border-slate-300 bg-white text-sm text-slate-900 placeholder-slate-400 focus:border-blue-500 focus:outline-none transition-all focus:ring-1 focus:ring-blue-500/20"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-700 transition-colors"
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              <FormError message={formError} />

              <button
                type="submit"
                disabled={isLoading}
                className="w-full py-3.5 mt-4 rounded-xl bg-blue-700 hover:bg-blue-800 text-white font-semibold text-sm transition-all active:scale-[0.98] disabled:opacity-50"
              >
                {isLoading ? "Memverifikasi..." : "Masuk Sekarang"}
              </button>
            </form>

            <div className="text-center mt-6">
              <p className="text-xs text-slate-500">
                Belum terdaftar?{" "}
                <Link href="/register" className="font-semibold text-blue-600 hover:text-blue-700 hover:underline transition-colors">Daftar akun gratis</Link>
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
