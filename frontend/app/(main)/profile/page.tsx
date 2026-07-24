"use client";

import React, { useState, useEffect, useRef, Suspense } from "react";
import { useRouter, useSearchParams, usePathname } from "next/navigation";
import { toast } from "sonner";
import {
    User,
    Mail,
    Shield,
    Camera,
    Loader2,
    ArrowLeft,
    Briefcase,
    Calendar,
    CalendarCheck,
    Link2Off
} from "lucide-react";
import { useProfile, useUpdateProfile, useUploadAvatar } from "@/hooks/useProfile";
import { extractApiError } from "@/lib/utils";
import { useCalendarStatus, useDisconnectCalendar } from "@/hooks/useCalendar";
import { getGoogleCalendarConnectUrl } from "@/lib/api";

interface ProfileFormState {
    name: string;
    email: string;
    job_title: string;
    department: string;
    bio: string;
}

const EMPTY_FORM: ProfileFormState = { name: "", email: "", job_title: "", department: "", bio: "" };

// useSearchParams() wajib dibungkus <Suspense> di Next.js App Router — kalau tidak,
// build produksi gagal ("missing-suspense-with-csr-bailout") karena halaman ini
// dicoba di-prerender statis. Diisolasi ke komponen kecil sendiri (tidak render
// apa-apa) supaya cuma bagian ini yang butuh boundary, bukan seluruh ProfilePage.
function CalendarRedirectHandler() {
    const router = useRouter();
    const pathname = usePathname();
    const searchParams = useSearchParams();

    // Redirect balik dari GET /auth/google/calendar/callback (lihat
    // plan/handoff-google-integration.md) — bersihkan query param dari URL
    // setelah ditampilkan supaya toast-nya tidak muncul lagi kalau di-refresh.
    useEffect(() => {
        const calendarParam = searchParams.get("calendar");
        if (!calendarParam) return;
        if (calendarParam === "connected") {
            toast.success("Google Calendar berhasil terhubung.");
        } else if (calendarParam === "error") {
            toast.error("Gagal menghubungkan Google Calendar. Coba lagi.");
        }
        router.replace(pathname);
    }, [searchParams, pathname, router]);

    return null;
}

export default function ProfilePage() {
    const router = useRouter();
    const [isEditing, setIsEditing] = useState(false);
    const { data: profile, isLoading, isError } = useProfile();
    const { mutate: updateProfile, isPending: isSaving } = useUpdateProfile();
    const { mutate: uploadAvatar, isPending: isUploadingAvatar } = useUploadAvatar();
    const { data: calendarStatus, isLoading: isCalendarLoading } = useCalendarStatus();
    const { mutate: disconnectCalendar, isPending: isDisconnecting } = useDisconnectCalendar();
    const avatarInputRef = useRef<HTMLInputElement>(null);

    const [formState, setFormState] = useState<ProfileFormState>(EMPTY_FORM);

    const handleDisconnectCalendar = () => {
        disconnectCalendar(undefined, {
            onSuccess: () => toast.success("Google Calendar terputus."),
            onError: () => toast.error("Gagal memutuskan Google Calendar. Coba lagi."),
        });
    };

    const MAX_AVATAR_SIZE = 5 * 1024 * 1024; // 5MB — belum ada batas resmi dari BE,
    // lihat plan/handoff-avatar-rsvp.md, ini cuma jaga-jaga sisi FE.

    const handleAvatarClick = () => avatarInputRef.current?.click();

    const handleAvatarChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        e.target.value = ""; // biar bisa pilih file yang sama lagi kalau mau ganti ulang
        if (!file) return;
        if (!file.type.startsWith("image/")) {
            toast.error("File harus berupa gambar.");
            return;
        }
        if (file.size > MAX_AVATAR_SIZE) {
            toast.error("Ukuran gambar maksimal 5MB.");
            return;
        }
        uploadAvatar(file, {
            onSuccess: () => toast.success("Foto profil berhasil diperbarui."),
            onError: (err) => toast.error(extractApiError(err, "Gagal mengunggah foto profil.")),
        });
    };

    // Sync form dari data server begitu tersedia (atau saat berubah dari luar edit mode)
    useEffect(() => {
        if (profile && !isEditing) {
            setFormState({
                name: profile.name ?? "",
                email: profile.email ?? "",
                job_title: profile.job_title ?? "",
                department: profile.department ?? "",
                bio: profile.bio ?? "",
            });
        }
    }, [profile, isEditing]);

    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>, key: keyof ProfileFormState) => {
        setFormState(prev => ({ ...prev, [key]: e.target.value }));
    };

    const handleCancel = () => {
        if (profile) {
            setFormState({
                name: profile.name ?? "",
                email: profile.email ?? "",
                job_title: profile.job_title ?? "",
                department: profile.department ?? "",
                bio: profile.bio ?? "",
            });
        }
        setIsEditing(false);
    };

    const handleSave = () => {
        updateProfile(formState, {
            onSuccess: (data) => {
                localStorage.setItem("user_profile", JSON.stringify(data));
                window.dispatchEvent(new Event("profileUpdate"));
                setIsEditing(false);
                toast.success("Profil berhasil disimpan.");
            },
            onError: () => {
                toast.error("Gagal menyimpan profil. Coba lagi.");
            },
        });
    };

    const joinDate = profile?.created_at
        ? new Date(profile.created_at).toLocaleDateString("id-ID", { month: "long", year: "numeric" })
        : "–";

    if (isLoading) {
        return (
            <main className="bg-slate-50 min-h-screen text-slate-900 pb-16 pt-8">
                <div className="max-w-5xl mx-auto px-6 space-y-6">
                    <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                        <div className="lg:col-span-4 h-72 rounded-2xl bg-slate-200/70 animate-pulse" />
                        <div className="lg:col-span-8 h-72 rounded-2xl bg-slate-200/70 animate-pulse" />
                    </div>
                </div>
            </main>
        );
    }

    if (isError || !profile) {
        return (
            <main className="bg-slate-50 min-h-screen text-slate-900 pb-16 pt-8">
                <div className="max-w-5xl mx-auto px-6">
                    <p className="text-center text-rose-400 py-10 text-sm">Gagal memuat profil. Pastikan backend sudah berjalan.</p>
                </div>
            </main>
        );
    }

    return (
        <main className="bg-slate-50 min-h-screen text-slate-900 pb-16 pt-8">
            <Suspense fallback={null}>
                <CalendarRedirectHandler />
            </Suspense>
            <div className="max-w-5xl mx-auto px-6 space-y-6">

                {/* Tombol Kembali */}
                <button
                    onClick={() => {
                        if (window.history.length > 1) {
                            router.back();
                        } else {
                            router.push('/meetings');
                        }
                    }}
                    className="inline-flex items-center gap-2 text-slate-500 hover:text-slate-900 transition text-xs font-medium mb-4 cursor-pointer"
                >
                    <ArrowLeft size={16} /> Kembali
                </button>

                <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 animate-in fade-in-0 slide-in-from-bottom-3 duration-300 delay-75">

                    {/* KOLOM KIRI: Foto & Info Singkat */}
                    <div className="lg:col-span-4 space-y-6">
                        <div className="bg-white border border-slate-200 shadow-sm rounded-2xl p-8 text-center space-y-5">
                            <div className="relative inline-block">
                                <div className="w-32 h-32 rounded-full border-2 border-indigo-200 p-1 mx-auto overflow-hidden">
                                    <div className="w-full h-full rounded-full bg-indigo-50 flex items-center justify-center overflow-hidden">
                                        {profile.avatar_url ? (
                                            // eslint-disable-next-line @next/next/no-img-element
                                            <img src={profile.avatar_url} alt={profile.name} className="w-full h-full object-cover" />
                                        ) : (
                                            <User size={60} className="text-indigo-600" />
                                        )}
                                    </div>
                                </div>
                                <input
                                    ref={avatarInputRef}
                                    type="file"
                                    accept="image/*"
                                    className="hidden"
                                    onChange={handleAvatarChange}
                                />
                                <button
                                    onClick={handleAvatarClick}
                                    disabled={isUploadingAvatar}
                                    title="Ganti foto profil"
                                    className="absolute bottom-1 right-1 p-2 bg-indigo-600 rounded-full text-white hover:bg-indigo-700 transition shadow-md disabled:opacity-60"
                                >
                                    {isUploadingAvatar ? <Loader2 size={16} className="animate-spin" /> : <Camera size={16} />}
                                </button>
                            </div>

                            <div>
                                <h2 className="text-xl font-bold text-slate-900">{profile.name}</h2>
                                {profile.job_title && <p className="text-sm text-slate-500">{profile.job_title}</p>}
                            </div>

                            <div className="pt-4 border-t border-slate-200 space-y-3">
                                {profile.department && (
                                    <div className="flex items-center gap-3 text-xs text-slate-500">
                                        <Briefcase size={14} className="text-indigo-600" />
                                        <span>{profile.department}</span>
                                    </div>
                                )}
                                <div className="flex items-center gap-3 text-xs text-slate-500">
                                    <Calendar size={14} className="text-indigo-600" />
                                    <span>Bergabung {joinDate}</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* KOLOM KANAN: Form Detail Profil */}
                    <div className="lg:col-span-8">
                        <div className="bg-white border border-slate-200 shadow-sm rounded-2xl p-8 h-full space-y-8">
                            <div className="flex items-center justify-between">
                                <h3 className="text-xl font-bold text-slate-900">Detail Profil</h3>
                                {!isEditing && (
                                    <button
                                        onClick={() => setIsEditing(true)}
                                        className="text-xs font-bold text-indigo-600 hover:text-indigo-800 transition"
                                    >
                                        Edit Profil
                                    </button>
                                )}
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                {/* Input Nama */}
                                <div className="space-y-2">
                                    <label className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Nama Lengkap</label>
                                    <div className="relative">
                                        <User className="absolute left-3 top-3 text-slate-400" size={16} />
                                        <input
                                            disabled={!isEditing}
                                            className="w-full bg-white border border-slate-300 rounded-xl py-2.5 pl-10 pr-4 outline-none text-sm text-slate-900 placeholder-slate-400 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/20 transition disabled:opacity-50 disabled:bg-slate-50"
                                            value={formState.name}
                                            onChange={(e) => handleInputChange(e, "name")}
                                        />
                                    </div>
                                </div>

                                {/* Input Email */}
                                <div className="space-y-2">
                                    <label className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Alamat Email</label>
                                    <div className="relative">
                                        <Mail className="absolute left-3 top-3 text-slate-400" size={16} />
                                        <input
                                            disabled={!isEditing}
                                            className="w-full bg-white border border-slate-300 rounded-xl py-2.5 pl-10 pr-4 outline-none text-sm text-slate-900 placeholder-slate-400 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/20 transition disabled:opacity-50 disabled:bg-slate-50"
                                            value={formState.email}
                                            onChange={(e) => handleInputChange(e, "email")}
                                        />
                                    </div>
                                </div>

                                {/* Input Jabatan */}
                                <div className="space-y-2">
                                    <label className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Jabatan</label>
                                    <div className="relative">
                                        <Shield className="absolute left-3 top-3 text-slate-400" size={16} />
                                        <input
                                            disabled={!isEditing}
                                            className="w-full bg-white border border-slate-300 rounded-xl py-2.5 pl-10 pr-4 outline-none text-sm text-slate-900 placeholder-slate-400 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/20 transition disabled:opacity-50 disabled:bg-slate-50"
                                            value={formState.job_title}
                                            onChange={(e) => handleInputChange(e, "job_title")}
                                        />
                                    </div>
                                </div>

                                {/* Input Departemen */}
                                <div className="space-y-2">
                                    <label className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Departemen</label>
                                    <div className="relative">
                                        <Briefcase className="absolute left-3 top-3 text-slate-400" size={16} />
                                        <input
                                            disabled={!isEditing}
                                            className="w-full bg-white border border-slate-300 rounded-xl py-2.5 pl-10 pr-4 outline-none text-sm text-slate-900 placeholder-slate-400 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/20 transition disabled:opacity-50 disabled:bg-slate-50"
                                            value={formState.department}
                                            onChange={(e) => handleInputChange(e, "department")}
                                        />
                                    </div>
                                </div>

                                {/* Textarea Bio */}
                                <div className="md:col-span-2 space-y-2">
                                    <label className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Bio Singkat</label>
                                    <textarea
                                        disabled={!isEditing}
                                        rows={3}
                                        className="w-full bg-white border border-slate-300 rounded-xl py-2.5 px-4 outline-none text-sm text-slate-900 placeholder-slate-400 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/20 transition disabled:opacity-50 disabled:bg-slate-50 resize-none"
                                        value={formState.bio}
                                        onChange={(e) => handleInputChange(e, "bio")}
                                    />
                                </div>
                            </div>

                            {/* Tombol Aksi */}
                            {isEditing && (
                                <div className="flex justify-end gap-3 pt-4 border-t border-slate-200">
                                    <button
                                        onClick={handleCancel}
                                        disabled={isSaving}
                                        className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-bold text-slate-500 hover:bg-slate-100 border border-slate-200 transition disabled:opacity-50"
                                    >
                                        Batal
                                    </button>
                                    <button
                                        onClick={handleSave}
                                        disabled={isSaving}
                                        className="flex items-center gap-2 px-6 py-2.5 rounded-xl text-xs font-bold bg-indigo-600 text-white hover:bg-indigo-700 transition shadow-sm disabled:opacity-50"
                                    >
                                        {isSaving ? "Menyimpan..." : "Simpan Perubahan"}
                                    </button>
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                {/* Integrasi Akun */}
                <div className="bg-white border border-slate-200 shadow-sm rounded-2xl p-8 animate-in fade-in-0 slide-in-from-bottom-3 duration-300 delay-150">
                    <h3 className="text-xl font-bold text-slate-900 mb-1">Integrasi Akun</h3>
                    <p className="text-xs text-slate-500 mb-6">Hubungkan Kioku dengan layanan lain.</p>

                    <div className="flex items-center justify-between gap-4 p-4 rounded-xl border border-slate-200">
                        <div className="flex items-center gap-3 min-w-0">
                            <div className="p-2.5 rounded-xl bg-indigo-50 text-indigo-600 shrink-0">
                                <CalendarCheck size={18} />
                            </div>
                            <div className="min-w-0">
                                <p className="text-sm font-semibold text-slate-900">Google Calendar</p>
                                <p className="text-xs text-slate-500 truncate">
                                    {isCalendarLoading
                                        ? "Memeriksa status koneksi..."
                                        : calendarStatus?.connected
                                            ? "Rapat kamu otomatis tersinkron ke kalender ini."
                                            : "Belum terhubung — rapat tidak otomatis masuk ke kalender."}
                                </p>
                            </div>
                        </div>

                        {calendarStatus?.connected ? (
                            <button
                                onClick={handleDisconnectCalendar}
                                disabled={isDisconnecting}
                                className="shrink-0 flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold text-rose-600 border border-rose-200 hover:bg-rose-50 transition disabled:opacity-50"
                            >
                                <Link2Off size={14} /> {isDisconnecting ? "Memutuskan..." : "Putuskan"}
                            </button>
                        ) : (
                            <button
                                onClick={() => { window.location.href = getGoogleCalendarConnectUrl(); }}
                                disabled={isCalendarLoading}
                                className="shrink-0 px-4 py-2 rounded-xl text-xs font-bold bg-indigo-600 text-white hover:bg-indigo-700 transition shadow-sm disabled:opacity-50"
                            >
                                Hubungkan
                            </button>
                        )}
                    </div>
                </div>
            </div>
        </main>
    );
}
