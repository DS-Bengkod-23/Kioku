"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Eye, EyeOff, ShieldCheck, User, Mail, Lock, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { FormError } from "@/components/ui/form-error";
import { extractApiError } from "@/lib/utils";

export default function RegisterPage() {
  const router = useRouter();
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    password: "",
    confirmPassword: ""
  });

  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isFlying, setIsFlying] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const [passwordStrength, setPasswordStrength] = useState({ score: 0, label: "Belum Diisi", color: "bg-slate-200" });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  useEffect(() => {
    const pass = formData.password;
    if (!pass) {
      setPasswordStrength({ score: 0, label: "Belum Diisi", color: "bg-slate-200" });
      return;
    }
    let score = 0;
    if (pass.length >= 8) score += 2;
    if (/[0-9]/.test(pass)) score++;
    if (/[A-Z]/.test(pass)) score++;
    if (/[^A-Za-z0-9]/.test(pass)) score++;

    if (score <= 2) setPasswordStrength({ score: 1, label: "Weak", color: "bg-rose-500" });
    else if (score <= 4) setPasswordStrength({ score: 2, label: "Medium", color: "bg-amber-500" });
    else setPasswordStrength({ score: 3, label: "Strong", color: "bg-emerald-500" });
  }, [formData.password]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    if (formData.password.length < 8) {
      setFormError("Password minimal 8 karakter.");
      return;
    }
    if (formData.password !== formData.confirmPassword) {
      setFormError("Konfirmasi password tidak cocok!");
      return;
    }

    setIsLoading(true);

    try {
      await import("@/lib/api").then(m =>
        m.registerUser({ name: formData.name, email: formData.email, password: formData.password })
      );
      toast.success("Pendaftaran berhasil! Silakan login.");
      setTimeout(() => {
        setIsFlying(true);
        setTimeout(() => router.push("/login"), 1000);
      }, 600);
    } catch (err: any) {
      setFormError(extractApiError(err, "Pendaftaran gagal. Coba lagi."));
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen bg-slate-50 text-slate-900 font-sans overflow-hidden relative items-center justify-center">

      {/* MAIN CONTAINER */}
      <div className="w-full max-w-6xl mx-auto px-6 grid lg:grid-cols-12 gap-12 items-center relative z-10">

        {/* TATA LETAK KIRI: Branding & Copywriting */}
        <div className="hidden lg:flex lg:col-span-5 flex-col space-y-8 text-left">
          <div className="flex items-center gap-3">
            <div className="h-6 w-6 rounded-lg bg-gradient-to-tr from-blue-800 to-blue-600 flex items-center justify-center">
              <div className="h-2 w-2 rounded-full bg-white animate-ping" />
            </div>
            <span className="font-bold text-base tracking-widest text-slate-900">KIOKU</span>
          </div>

          <div className="space-y-4">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-slate-200 bg-blue-50 text-xs text-blue-600 font-medium">
              <Sparkles size={12} /> Powered by Advanced AI Insights
            </div>
            <h1 className="text-4xl xl:text-5xl font-black tracking-tight leading-[1.15] text-slate-900">
              Mulai Sesi Rapat <br />
              <span className="text-blue-700">
                Pintar Anda.
              </span>
            </h1>
            <p className="text-sm text-slate-500 leading-relaxed max-w-sm">
              Gabung sekarang dan nikmati pencatatan berbasis AI otomatis, pembuatan poin tugas instan, dan kolaborasi cerdas.
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
          <div className="text-[11px] text-slate-500">&copy; {new Date().getFullYear()} Kioku. All rights reserved.</div>
        </div>

        {/* TATA LETAK KANAN: Form Boks */}
        <div className="w-full lg:col-span-7 flex justify-center lg:justify-end">
          <div
            className={`w-full max-w-lg bg-white rounded-[32px] shadow-lg border border-slate-200 p-8 md:p-10
              transition-all duration-1000 ease-in-out transform relative overflow-hidden
              ${isFlying ? "opacity-0 -translate-y-[100vh] scale-75 rotate-6 blur-md" : "opacity-100 translate-y-0 scale-100"}`}
          >
            <div className="mb-8">
              <h2 className="text-2xl font-extrabold tracking-wide text-slate-900">Daftar Akun Baru</h2>
              <p className="text-xs text-slate-500 mt-2 font-medium">Lengkapi data akun Kioku Anda</p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              {/* FIELD NAMA */}
              <div className="space-y-2">
                <label className="block text-[11px] font-bold text-slate-500 uppercase tracking-widest">Nama Lengkap</label>
                <div className="relative">
                  <User size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
                  <input
                    type="text"
                    name="name"
                    disabled={isLoading}
                    placeholder="John Doe"
                    value={formData.name}
                    onChange={handleChange}
                    className="w-full pl-11 pr-4 py-3 rounded-xl border border-slate-300 bg-white text-sm text-slate-900 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500/20 transition-all placeholder-slate-400"
                    required
                  />
                </div>
              </div>

              {/* FIELD EMAIL */}
              <div className="space-y-2">
                <label className="block text-[11px] font-bold text-slate-500 uppercase tracking-widest">Email Address</label>
                <div className="relative">
                  <Mail size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
                  <input
                    type="email"
                    name="email"
                    disabled={isLoading}
                    placeholder="name@example.com"
                    value={formData.email}
                    onChange={handleChange}
                    className="w-full pl-11 pr-4 py-3 rounded-xl border border-slate-300 bg-white text-sm text-slate-900 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500/20 transition-all placeholder-slate-400"
                    required
                  />
                </div>
              </div>

              {/* FIELD PASSWORD */}
              <div className="space-y-2">
                <label className="block text-[11px] font-bold text-slate-500 uppercase tracking-widest">Password</label>
                <div className="relative">
                  <Lock size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
                  <input
                    type={showPassword ? "text" : "password"}
                    name="password"
                    disabled={isLoading}
                    placeholder="••••••••"
                    value={formData.password}
                    onChange={handleChange}
                    className="w-full pl-11 pr-10 py-3 rounded-xl border border-slate-300 bg-white text-sm text-slate-900 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500/20 transition-all placeholder-slate-400"
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

                {formData.password && (
                  <div className="pt-1 space-y-1.5 px-0.5">
                    <div className="flex justify-between items-center text-[10px] font-bold">
                      <span className="text-slate-500">Kekuatan Sandi:</span>
                      <span className={passwordStrength.score === 1 ? "text-rose-600" : passwordStrength.score === 2 ? "text-amber-700" : "text-emerald-700"}>
                        {passwordStrength.label}
                      </span>
                    </div>
                    <div className="h-[3px] w-full bg-slate-200 rounded-full overflow-hidden">
                      <div className={`h-full ${passwordStrength.color} transition-all duration-500`} style={{ width: passwordStrength.score === 1 ? "33%" : passwordStrength.score === 2 ? "66%" : "100%" }} />
                    </div>
                  </div>
                )}
              </div>

              {/* FIELD KONFIRMASI PASSWORD */}
              <div className="space-y-2">
                <label className="block text-[11px] font-bold text-slate-500 uppercase tracking-widest">Konfirmasi Password</label>
                <div className="relative">
                  <Lock size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
                  <input
                    type={showConfirmPassword ? "text" : "password"}
                    name="confirmPassword"
                    disabled={isLoading}
                    placeholder="••••••••"
                    value={formData.confirmPassword}
                    onChange={handleChange}
                    className={`w-full pl-11 pr-10 py-3 rounded-xl border bg-white text-sm text-slate-900 focus:outline-none focus:ring-1 transition-all placeholder-slate-400 ${formData.confirmPassword && formData.password !== formData.confirmPassword
                      ? "border-rose-500/40 focus:border-rose-500 focus:ring-rose-500/20"
                      : "border-slate-300 focus:border-blue-500 focus:ring-blue-500/20"
                      }`}
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-700 transition-colors"
                  >
                    {showConfirmPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
                {formData.confirmPassword && formData.password !== formData.confirmPassword && (
                  <p className="text-[10px] text-rose-400 font-medium tracking-wide">Sandi tidak cocok!</p>
                )}
              </div>

              <FormError message={formError} />

              <button
                type="submit"
                disabled={isLoading}
                className="w-full py-3 mt-4 rounded-xl bg-blue-700 hover:bg-blue-800 text-white font-bold text-sm transition-all active:scale-[0.99] disabled:opacity-50"
              >
                {isLoading ? "Mendaftarkan..." : "Daftar Akun Baru"}
              </button>
            </form>

            <div className="text-center mt-6">
              <p className="text-xs text-slate-500 font-medium">
                Sudah memiliki akun?{" "}
                <Link href="/login" className="font-bold text-blue-600 hover:text-blue-700 hover:underline ml-0.5">
                  Masuk di sini
                </Link>
              </p>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
