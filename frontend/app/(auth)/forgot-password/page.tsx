"use client";

import React from "react";
import Link from "next/link";
import { ArrowLeft, Mail, ShieldCheck } from "lucide-react";

export default function ForgotPasswordPage() {
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
                        <span className="font-bold text-base tracking-widest text-slate-900">MEETMATE</span>
                    </div>

                    <div className="space-y-4">
                        <h1 className="text-4xl xl:text-5xl font-black tracking-tight leading-[1.15] text-slate-900">
                            Amankan Kembali <br />
                            <span className="text-blue-700">
                                Akun Anda.
                            </span>
                        </h1>
                        <p className="text-sm text-slate-500 leading-relaxed max-w-sm">
                            Pemulihan password mandiri belum tersedia saat ini. Hubungi admin untuk bantuan mengakses kembali akun Anda.
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

                {/* BAGIAN KANAN: Notice */}
                <div className="w-full lg:col-span-7 flex items-center justify-center p-6 lg:p-12 relative z-10">
                    <div className="w-full max-w-md bg-white rounded-3xl shadow-lg border border-slate-200 p-8 md:p-10 text-center">
                        <div className="mx-auto mb-6 h-14 w-14 rounded-full bg-blue-50 text-blue-700 flex items-center justify-center">
                            <Mail size={26} />
                        </div>

                        <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Fitur Belum Tersedia</h2>
                        <p className="text-sm text-slate-500 mt-3 leading-relaxed">
                            Pemulihan password secara mandiri masih dalam pengembangan. Untuk saat ini, silakan hubungi
                            admin/organizer tim Anda untuk mendapatkan bantuan reset password.
                        </p>

                        <Link
                            href="/login"
                            className="mt-8 inline-flex items-center gap-2 justify-center w-full py-3.5 rounded-xl bg-blue-700 hover:bg-blue-800 text-white font-semibold text-sm transition-all active:scale-[0.98]"
                        >
                            <ArrowLeft size={16} /> Kembali ke Halaman Masuk
                        </Link>
                    </div>
                </div>
            </div>
        </div>
    );
}
