"use client";

import React, { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { Eye, EyeOff, ShieldCheck, Lock } from "lucide-react";
import { toast } from "sonner";
import { FormError } from "@/components/ui/form-error";
import { confirmResetPassword } from "@/lib/api";
import { extractApiError } from "@/lib/utils";

// Halaman publik (no auth) — tujuan link dari email reset password yang dikirim
// lewat POST /admin/users/{id}/reset-password (superadmin). Lihat
// plan/admin-role-frontend-handoff.md bagian 4.
export default function ResetPasswordPage() {
    const { token } = useParams<{ token: string }>();
    const router = useRouter();
    const [password, setPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [showPassword, setShowPassword] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const [formError, setFormError] = useState<string | null>(null);
    const [done, setDone] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setFormError(null);

        if (password.length < 8) {
            setFormError("Password minimal 8 karakter.");
            return;
        }
        if (password !== confirmPassword) {
            setFormError("Konfirmasi password tidak cocok!");
            return;
        }

        setIsLoading(true);
        try {
            await confirmResetPassword(token, password);
            setDone(true);
            toast.success("Password berhasil diperbarui!");
            setTimeout(() => router.replace("/login"), 1500);
        } catch (err: any) {
            setFormError(extractApiError(err, "Link reset tidak valid atau sudah kedaluwarsa."));
            setIsLoading(false);
        }
    };

    return (
        <div className="flex min-h-screen bg-slate-50 text-slate-900 font-sans items-center justify-center p-6">
            <div className="w-full max-w-md bg-white rounded-3xl shadow-lg border border-slate-200 p-8 md:p-10">
                <div className="mb-8 text-center">
                    <div className="mx-auto mb-4 h-12 w-12 rounded-full bg-blue-50 text-blue-700 flex items-center justify-center">
                        <ShieldCheck size={22} />
                    </div>
                    <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Atur Ulang Password</h2>
                    <p className="text-xs text-slate-500 mt-1.5">Masukkan password baru untuk akun kamu</p>
                </div>

                {done ? (
                    <p className="text-center text-sm text-emerald-600 font-medium">
                        Password berhasil diperbarui. Mengarahkan ke halaman masuk...
                    </p>
                ) : (
                    <form onSubmit={handleSubmit} className="space-y-5">
                        <div className="space-y-2">
                            <label className="block text-[11px] font-bold text-slate-500 uppercase tracking-widest">Password Baru</label>
                            <div className="relative">
                                <Lock size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
                                <input
                                    type={showPassword ? "text" : "password"}
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    placeholder="••••••••"
                                    disabled={isLoading}
                                    className="w-full pl-11 pr-10 py-3 rounded-xl border border-slate-300 bg-white text-sm text-slate-900 focus:border-blue-500 focus:outline-none transition-all focus:ring-1 focus:ring-blue-500/20"
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

                        <div className="space-y-2">
                            <label className="block text-[11px] font-bold text-slate-500 uppercase tracking-widest">Konfirmasi Password</label>
                            <div className="relative">
                                <Lock size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
                                <input
                                    type={showPassword ? "text" : "password"}
                                    value={confirmPassword}
                                    onChange={(e) => setConfirmPassword(e.target.value)}
                                    placeholder="••••••••"
                                    disabled={isLoading}
                                    className="w-full pl-11 pr-4 py-3 rounded-xl border border-slate-300 bg-white text-sm text-slate-900 focus:border-blue-500 focus:outline-none transition-all focus:ring-1 focus:ring-blue-500/20"
                                    required
                                />
                            </div>
                        </div>

                        <FormError message={formError} />

                        <button
                            type="submit"
                            disabled={isLoading}
                            className="w-full py-3.5 mt-2 rounded-xl bg-blue-700 hover:bg-blue-800 text-white font-semibold text-sm transition-all active:scale-[0.98] disabled:opacity-50"
                        >
                            {isLoading ? "Menyimpan..." : "Simpan Password Baru"}
                        </button>
                    </form>
                )}

                <div className="text-center mt-6">
                    <Link href="/login" className="text-xs text-slate-500 hover:text-blue-600 hover:underline transition-colors">
                        Kembali ke halaman masuk
                    </Link>
                </div>
            </div>
        </div>
    );
}
