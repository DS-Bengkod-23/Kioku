"use client";

import { useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ArrowLeft, ShieldCheck, Users, Video, ScrollText } from "lucide-react";
import { useProfile } from "@/hooks/useProfile";
import { cn } from "@/lib/utils";

// Route terpisah dari (main) — sesuai plan/admin-role-design.md ("bukan menempel
// ke dashboard biasa"). Guard di sini murni cek `role` dari GET /auth/me
// (plan/admin-role-frontend-handoff.md) — kalau bukan admin/superadmin, tendang
// balik ke /meetings. Default aman ke arah "bukan admin" kalau `role` belum ada
// sama sekali di response (mis. BE belum live).
export default function AdminLayout({ children }: { children: React.ReactNode }) {
    const router = useRouter();
    const pathname = usePathname();
    const { data: profile, isLoading } = useProfile();
    const isAdmin = !!profile?.role && profile.role !== "user";

    useEffect(() => {
        if (!isLoading && !isAdmin) {
            router.replace("/meetings");
        }
    }, [isLoading, isAdmin, router]);

    if (isLoading || !isAdmin) {
        return (
            <div className="w-full min-h-screen bg-slate-50 flex items-center justify-center text-slate-500 text-xs font-medium">
                Memeriksa akses...
            </div>
        );
    }

    const isActive = (href: string) => pathname.startsWith(href);

    return (
        <div className="w-full min-h-screen flex flex-col bg-slate-50">
            <header className="w-full border-b border-slate-200 bg-white sticky top-0 z-50">
                <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between gap-6">
                    <div className="flex items-center gap-6 min-w-0">
                        <div className="flex items-center gap-2 shrink-0">
                            <div className="h-8 w-8 rounded-lg bg-slate-900 flex items-center justify-center rotate-3">
                                <ShieldCheck size={15} className="text-white" />
                            </div>
                            <span className="font-display font-bold text-lg tracking-tight text-slate-900">Admin</span>
                        </div>

                        <nav className="hidden md:flex items-center gap-1 text-sm font-medium">
                            <Link
                                href="/admin/users"
                                className={cn(
                                    "flex items-center gap-2 px-3.5 py-2 rounded-lg transition-all",
                                    isActive("/admin/users") ? "bg-slate-900 text-white" : "text-slate-500 hover:bg-slate-100"
                                )}
                            >
                                <Users size={14} /> Pengguna
                            </Link>
                            <Link
                                href="/admin/meetings"
                                className={cn(
                                    "flex items-center gap-2 px-3.5 py-2 rounded-lg transition-all",
                                    isActive("/admin/meetings") ? "bg-slate-900 text-white" : "text-slate-500 hover:bg-slate-100"
                                )}
                            >
                                <Video size={14} /> Rapat
                            </Link>
                            <Link
                                href="/admin/audit-logs"
                                className={cn(
                                    "flex items-center gap-2 px-3.5 py-2 rounded-lg transition-all",
                                    isActive("/admin/audit-logs") ? "bg-slate-900 text-white" : "text-slate-500 hover:bg-slate-100"
                                )}
                            >
                                <ScrollText size={14} /> Audit Log
                            </Link>
                        </nav>
                    </div>

                    <div className="flex items-center gap-3 shrink-0">
                        <span className="hidden sm:inline text-[10px] font-bold uppercase tracking-wider bg-slate-100 text-slate-500 px-2.5 py-1 rounded-full">
                            {profile?.role}
                        </span>
                        <Link
                            href="/meetings"
                            className="flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-slate-900 transition"
                        >
                            <ArrowLeft size={14} /> Kembali ke App
                        </Link>
                    </div>
                </div>
            </header>

            <main className="w-full flex-1">{children}</main>
        </div>
    );
}
