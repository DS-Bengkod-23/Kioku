"use client";

import { useState, useRef, useEffect } from "react";
import { Video, CheckSquare, Calendar, User, LogOut } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { logoutUser } from "@/lib/api";
import { cn } from "@/lib/utils";
import ReminderBell from "@/components/ReminderBell";

export default function MainDashboardLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const [isOpen, setIsOpen] = useState(false);
    const dropdownRef = useRef<HTMLDivElement>(null);
    const pathname = usePathname();
    const isActive = (href: string) => pathname.startsWith(href);

    const [profileName, setProfileName] = useState("John Doe");

    const loadProfileData = () => {
        const savedProfile = localStorage.getItem("user_profile");
        if (savedProfile) {
            try {
                const parsed = JSON.parse(savedProfile);
                if (parsed.name) setProfileName(parsed.name);
            } catch {
                localStorage.removeItem("user_profile");
            }
        }
    };

    const getInitials = (name: string) => {
        const parts = name.split(" ");
        if (parts.length >= 2) {
            return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
        }
        return name.slice(0, 2).toUpperCase();
    };

    useEffect(() => {
        loadProfileData();
        window.addEventListener("profileUpdate", loadProfileData);
        const handleClickOutside = (event: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setIsOpen(false);
            }
        };
        document.addEventListener("mousedown", handleClickOutside);
        return () => {
            document.removeEventListener("mousedown", handleClickOutside);
            window.removeEventListener("profileUpdate", loadProfileData);
        };
    }, []);

    return (
        <div className="w-full min-h-screen flex flex-col bg-slate-50 overflow-x-hidden">
            <header className="w-full border-b border-slate-200 bg-white sticky top-0 z-50">
                <div className="max-w-7xl mx-auto px-6 h-16 grid grid-cols-3 items-center">

                    {/* Logo */}
                    <div className="flex items-center justify-start gap-2.5">
                        <div className="h-8 w-8 rounded-lg bg-indigo-600 flex items-center justify-center rotate-3">
                            <Video size={15} className="text-white" />
                        </div>
                        <span className="font-display font-bold text-lg tracking-tight text-slate-900">Kioku</span>
                    </div>

                    {/* Navigasi */}
                    <nav className="hidden md:flex items-center justify-center gap-1 text-sm font-medium">
                        <Link
                            href="/meetings"
                            className={cn(
                                "flex items-center gap-2 px-4 py-2 rounded-lg border-b-2 transition-all",
                                isActive("/meetings")
                                    ? "text-indigo-700 font-bold border-indigo-600"
                                    : "text-slate-400 hover:text-slate-700 border-transparent"
                            )}
                        >
                            <Video size={15} /> Rapat
                        </Link>
                        <Link
                            href="/calendar"
                            className={cn(
                                "flex items-center gap-2 px-4 py-2 rounded-lg border-b-2 transition-all",
                                isActive("/calendar")
                                    ? "text-indigo-700 font-bold border-indigo-600"
                                    : "text-slate-400 hover:text-slate-700 border-transparent"
                            )}
                        >
                            <Calendar size={15} /> Kalender
                        </Link>
                        <Link
                            href="/action-items"
                            className={cn(
                                "flex items-center gap-2 px-4 py-2 rounded-lg border-b-2 transition-all",
                                isActive("/action-items")
                                    ? "text-indigo-700 font-bold border-indigo-600"
                                    : "text-slate-400 hover:text-slate-700 border-transparent"
                            )}
                        >
                            <CheckSquare size={15} /> Tugas Saya
                        </Link>
                    </nav>

                    {/* Reminder Bell & Avatar */}
                    <div className="flex items-center justify-end gap-3 relative" ref={dropdownRef}>
                        <ReminderBell />
                        <button
                            onClick={() => setIsOpen(!isOpen)}
                            className="flex items-center gap-2.5 bg-slate-50 border border-slate-200 hover:border-indigo-300 px-3 py-1.5 rounded-full transition-all cursor-pointer"
                        >
                            <div className="h-6 w-6 rounded-full bg-indigo-600 text-[10px] font-bold flex items-center justify-center text-white">
                                {getInitials(profileName)}
                            </div>
                            <span className="text-xs font-semibold text-slate-700 hidden sm:inline">{profileName}</span>
                        </button>

                        {isOpen && (
                            <div className="absolute top-full right-0 mt-2 w-44 bg-white border border-slate-200 rounded-xl shadow-xl shadow-slate-200/60 overflow-hidden animate-in fade-in zoom-in duration-150">
                                <Link
                                    href="/profile"
                                    onClick={() => setIsOpen(false)}
                                    className="flex items-center gap-3 px-4 py-3 text-xs text-slate-600 hover:bg-slate-50 hover:text-slate-900 transition"
                                >
                                    <User size={14} /> Personal Info
                                </Link>
                                <div className="mx-3 border-t border-slate-100" />
                                <button
                                    onClick={() => logoutUser()}
                                    className="flex items-center gap-3 px-4 py-3 text-xs text-rose-500 hover:bg-rose-50 w-full transition"
                                >
                                    <LogOut size={14} /> Log Out
                                </button>
                            </div>
                        )}
                    </div>
                </div>
            </header>

            <main className="w-full flex-1">{children}</main>
        </div>
    );
}
