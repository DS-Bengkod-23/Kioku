"use client";

import { useState, useRef, useEffect } from "react";
import { Video, CheckSquare, User, LogOut } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { logoutUser } from "@/lib/api";

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
                        <div className="h-7 w-7 rounded-lg bg-blue-800 flex items-center justify-center">
                            <Video size={14} className="text-white" />
                        </div>
                        <span className="font-bold text-lg tracking-wide text-slate-900">MeetMate</span>
                    </div>

                    {/* Navigasi */}
                    <nav className="hidden md:flex items-center justify-center gap-2 text-sm font-medium">
                        <Link
                            href="/meetings"
                            className={isActive("/meetings")
                                ? "bg-blue-50 text-blue-700 font-semibold flex items-center gap-2 px-3 py-1.5 rounded-lg"
                                : "text-slate-500 hover:text-blue-700 hover:bg-slate-50 flex items-center gap-2 px-3 py-1.5 rounded-lg transition"
                            }
                        >
                            <Video size={16} /> Rapat
                        </Link>
                        <Link
                            href="/action-items"
                            className={isActive("/action-items")
                                ? "bg-blue-50 text-blue-700 font-semibold flex items-center gap-2 px-3 py-1.5 rounded-lg"
                                : "text-slate-500 hover:text-blue-700 hover:bg-slate-50 flex items-center gap-2 px-3 py-1.5 rounded-lg transition"
                            }
                        >
                            <CheckSquare size={16} /> Tugas Saya
                        </Link>
                    </nav>

                    {/* Avatar & Dropdown */}
                    <div className="flex items-center justify-end relative" ref={dropdownRef}>
                        <button
                            onClick={() => setIsOpen(!isOpen)}
                            className="flex items-center gap-2.5 bg-slate-100 border border-slate-200 px-3 py-1.5 rounded-full hover:border-blue-300 transition-all cursor-pointer"
                        >
                            <div className="h-6 w-6 rounded-full bg-blue-800 text-[10px] font-bold flex items-center justify-center text-white">
                                {getInitials(profileName)}
                            </div>
                            <span className="text-xs font-semibold text-slate-700 hidden sm:inline">{profileName}</span>
                        </button>

                        {isOpen && (
                            <div className="absolute top-full right-0 mt-2 w-44 bg-white border border-slate-200 rounded-xl shadow-lg overflow-hidden animate-in fade-in zoom-in duration-200">
                                <Link
                                    href="/profile"
                                    onClick={() => setIsOpen(false)}
                                    className="flex items-center gap-3 px-4 py-3 text-xs text-slate-600 hover:bg-slate-50 hover:text-slate-900 transition"
                                >
                                    <User size={14} /> Personal Info
                                </Link>
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
