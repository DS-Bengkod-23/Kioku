"use client";

import { useEffect, useState } from "react";
import { Bell, BellOff } from "lucide-react";
import { cn } from "@/lib/utils";
import { useActionItemReminders } from "@/hooks/useActionItemReminders";

export default function ReminderBell() {
  const [permission, setPermission] = useState<NotificationPermission | "unsupported">("default");

  useEffect(() => {
    if (typeof window === "undefined" || !("Notification" in window)) {
      setPermission("unsupported");
      return;
    }
    setPermission(Notification.permission);
  }, []);

  // Hook ini sendiri gak ngapa-ngapain selama permission belum "granted" — aman
  // dipasang di sini terlepas dari state permission-nya sekarang.
  useActionItemReminders();

  if (permission === "unsupported") return null;

  const handleClick = async () => {
    if (permission !== "default") return;
    const result = await Notification.requestPermission();
    setPermission(result);
  };

  return (
    <button
      onClick={handleClick}
      disabled={permission !== "default"}
      title={
        permission === "granted"
          ? "Notifikasi tugas mendekati deadline aktif"
          : permission === "denied"
          ? "Notifikasi diblokir di pengaturan browser"
          : "Aktifkan notifikasi buat tugas mendekati deadline"
      }
      className={cn(
        "p-2 rounded-full border transition shrink-0",
        permission === "granted"
          ? "bg-indigo-50 border-indigo-200 text-indigo-600"
          : permission === "denied"
          ? "bg-slate-50 border-slate-200 text-slate-300 cursor-not-allowed"
          : "bg-white border-slate-200 text-slate-400 hover:text-indigo-600 hover:border-indigo-300"
      )}
    >
      {permission === "denied" ? <BellOff size={15} /> : <Bell size={15} />}
    </button>
  );
}
