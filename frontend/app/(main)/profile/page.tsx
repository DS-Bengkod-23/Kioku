"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
    User,
    Mail,
    Shield,
    Camera,
    ArrowLeft,
    Briefcase,
    Calendar
} from "lucide-react";
//import { cn } from "@/lib/utils";

export default function ProfilePage() {
    const router = useRouter();
    const [mounted, setMounted] = useState(false);
    const [isEditing, setIsEditing] = useState(false);

    // 1. State Utama untuk menampung Data Profil
    const [userData, setUserData] = useState({
        name: "John Doe",
        email: "john.doe@company.com",
        role: "Senior Project Manager",
        department: "Engineering",
        joinDate: "Januari 2024",
        bio: "Berfokus pada efisiensi tim dan optimasi workflow menggunakan teknologi AI."
    });

    // Temporary state untuk menampung ketikan form sebelum di-save
    const [formState, setFormState] = useState({ ...userData });

    // 2. Ambil data profil dari localStorage saat komponen pertama kali di-render
    useEffect(() => {
        setMounted(true);
        const savedProfile = localStorage.getItem("user_profile");
        if (savedProfile) {
            const parsed = JSON.parse(savedProfile);
            setUserData(parsed);
            setFormState(parsed);
        }
    }, []);

    // 3. Fungsi penangan perubahan teks pada form input
    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>, key: string) => {
        setFormState(prev => ({
            ...prev,
            [key]: e.target.value
        }));
    };

    // 4. Fungsi tombol Batal (mengembalikan form ke data asli)
    const handleCancel = () => {
        setFormState({ ...userData });
        setIsEditing(false);
    };

    // 5. Fungsi tombol Simpan Perubahan (Commit ke LocalStorage & State)
    const handleSave = () => {
        setUserData(formState);
        localStorage.setItem("user_profile", JSON.stringify(formState));
        setIsEditing(false);

        // Memicu custom event agar Layout Navbar langsung ikut ter-update saat itu juga
        window.dispatchEvent(new Event("profileUpdate"));
    };

    if (!mounted) return null;

    return (
        <main className="bg-[#0A051B] min-h-screen text-slate-100 pb-16 pt-8 relative overflow-hidden">
            {/* Efek Pendar Latar Belakang */}
            <div className="absolute top-[-10%] right-[-5%] w-[400px] h-[400px] bg-[#7E61F2]/10 rounded-full blur-[120px] pointer-events-none" />

            <div className="max-w-5xl mx-auto px-6 space-y-6 relative z-10">

                {/* Tombol Kembali */}
                <button
                    onClick={() => {
                        if (window.history.length > 1) {
                            router.back();
                        } else {
                            router.push('/dashboard');
                        }
                    }}
                    className="relative z-50 inline-flex items-center gap-2 text-slate-400 hover:text-white transition text-xs font-medium mb-4 cursor-pointer"
                >
                    <ArrowLeft size={16} /> Kembali
                </button>

                <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">

                    {/* KOLOM KIRI: Foto & Info Singkat */}
                    <div className="lg:col-span-4 space-y-6">
                        <div className="bg-[#130E29]/60 backdrop-blur-md border border-purple-500/10 rounded-3xl p-8 text-center space-y-5">
                            <div className="relative inline-block">
                                <div className="w-32 h-32 rounded-full border-2 border-[#7E61F2] p-1 mx-auto overflow-hidden">
                                    <div className="w-full h-full rounded-full bg-purple-900/30 flex items-center justify-center">
                                        <User size={60} className="text-[#7E61F2]" />
                                    </div>
                                </div>
                                <button className="absolute bottom-1 right-1 p-2 bg-[#7E61F2] rounded-full text-white hover:bg-[#6D4EE0] transition shadow-lg">
                                    <Camera size={16} />
                                </button>
                            </div>

                            <div>
                                <h2 className="text-xl font-bold text-white">{userData.name}</h2>
                                <p className="text-sm text-slate-400">{userData.role}</p>
                            </div>

                            <div className="pt-4 border-t border-purple-500/10 space-y-3">
                                <div className="flex items-center gap-3 text-xs text-slate-400">
                                    <Briefcase size={14} className="text-purple-400" />
                                    <span>{userData.department}</span>
                                </div>
                                <div className="flex items-center gap-3 text-xs text-slate-400">
                                    <Calendar size={14} className="text-purple-400" />
                                    <span>Bergabung {userData.joinDate}</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* KOLOM KANAN: Form Detail Profil */}
                    <div className="lg:col-span-8">
                        <div className="bg-[#130E29]/40 backdrop-blur-lg rounded-3xl p-8 border border-purple-500/10 h-full space-y-8">
                            <div className="flex items-center justify-between">
                                <h3 className="text-xl font-bold text-white">Detail Profil</h3>
                                {!isEditing && (
                                    <button
                                        onClick={() => setIsEditing(true)}
                                        className="text-xs font-bold text-[#7E61F2] hover:text-white transition"
                                    >
                                        Edit Profil
                                    </button>
                                )}
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                {/* Input Nama */}
                                <div className="space-y-2">
                                    <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Nama Lengkap</label>
                                    <div className="relative">
                                        <User className="absolute left-3 top-3 text-slate-500" size={16} />
                                        <input
                                            disabled={!isEditing}
                                            className="w-full bg-[#0A051B] border border-purple-500/10 rounded-xl py-2.5 pl-10 pr-4 outline-none text-sm disabled:opacity-50 text-slate-200"
                                            value={formState.name}
                                            onChange={(e) => handleInputChange(e, "name")}
                                        />
                                    </div>
                                </div>

                                {/* Input Email */}
                                <div className="space-y-2">
                                    <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Alamat Email</label>
                                    <div className="relative">
                                        <Mail className="absolute left-3 top-3 text-slate-500" size={16} />
                                        <input
                                            disabled={!isEditing}
                                            className="w-full bg-[#0A051B] border border-purple-500/10 rounded-xl py-2.5 pl-10 pr-4 outline-none text-sm disabled:opacity-50 text-slate-200"
                                            value={formState.email}
                                            onChange={(e) => handleInputChange(e, "email")}
                                        />
                                    </div>
                                </div>

                                {/* Input Jabatan */}
                                <div className="space-y-2">
                                    <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Jabatan</label>
                                    <div className="relative">
                                        <Shield className="absolute left-3 top-3 text-slate-500" size={16} />
                                        <input
                                            disabled={!isEditing}
                                            className="w-full bg-[#0A051B] border border-purple-500/10 rounded-xl py-2.5 pl-10 pr-4 outline-none text-sm disabled:opacity-50 text-slate-200"
                                            value={formState.role}
                                            onChange={(e) => handleInputChange(e, "role")}
                                        />
                                    </div>
                                </div>

                                {/* Input Departemen */}
                                <div className="space-y-2">
                                    <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Departemen</label>
                                    <div className="relative">
                                        <Briefcase className="absolute left-3 top-3 text-slate-500" size={16} />
                                        <input
                                            disabled={!isEditing}
                                            className="w-full bg-[#0A051B] border border-purple-500/10 rounded-xl py-2.5 pl-10 pr-4 outline-none text-sm disabled:opacity-50 text-slate-200"
                                            value={formState.department}
                                            onChange={(e) => handleInputChange(e, "department")}
                                        />
                                    </div>
                                </div>

                                {/* Textarea Bio */}
                                <div className="md:col-span-2 space-y-2">
                                    <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Bio Singkat</label>
                                    <textarea
                                        disabled={!isEditing}
                                        rows={3}
                                        className="w-full bg-[#0A051B] border border-purple-500/10 rounded-xl py-2.5 px-4 outline-none text-sm disabled:opacity-50 resize-none text-slate-200"
                                        value={formState.bio}
                                        onChange={(e) => handleInputChange(e, "bio")}
                                    />
                                </div>
                            </div>

                            {/* Tombol Aksi */}
                            {isEditing && (
                                <div className="flex justify-end gap-3 pt-4">
                                    <button
                                        onClick={handleCancel}
                                        className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-bold text-slate-400 hover:bg-white/5 transition"
                                    >
                                        Batal
                                    </button>
                                    <button
                                        onClick={handleSave}
                                        className="flex items-center gap-2 px-6 py-2.5 rounded-xl text-xs font-bold bg-[#7E61F2] text-white hover:bg-[#6D4EE0] transition shadow-lg shadow-[#7E61F2]/20"
                                    >
                                        Simpan Perubahan
                                    </button>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </main>
    );
}