import { useEffect } from "react";
import { useMyActionItems } from "@/hooks/useActionItems";
import { daysUntil } from "@/lib/utils";

const NOTIFIED_KEY = "notified_action_item_ids";

// Reminder ringan — cuma jalan selagi app kebuka di tab ini (beda dari reminder
// email H-1 yang perlu BE, lihat plan/handoff-audio-playback-reminder.md). Ini
// lapisan tambahan buat kasih sinyal lebih cepat, bukan pengganti versi email.
function getNotifiedIds(): Set<string> {
  if (typeof window === "undefined") return new Set();
  try {
    const raw = localStorage.getItem(NOTIFIED_KEY);
    return raw ? new Set(JSON.parse(raw)) : new Set();
  } catch {
    return new Set();
  }
}

function markNotified(id: string) {
  const ids = getNotifiedIds();
  ids.add(id);
  localStorage.setItem(NOTIFIED_KEY, JSON.stringify(Array.from(ids)));
}

export function useActionItemReminders() {
  const { data } = useMyActionItems("open");

  useEffect(() => {
    if (typeof window === "undefined" || !("Notification" in window)) return;
    if (Notification.permission !== "granted") return;
    if (!data?.items) return;

    const notifiedIds = getNotifiedIds();
    for (const item of data.items) {
      if (!item.due_date || notifiedIds.has(item.id)) continue;
      // H-1: besok, hari ini, atau udah lewat (daysUntil bisa negatif)
      if (daysUntil(item.due_date) <= 1) {
        const isOverdue = daysUntil(item.due_date) < 0;
        new Notification(isOverdue ? "Tugas terlambat" : "Tugas mendekati deadline", {
          body: `${item.task} — ${item.meeting.title}`,
          tag: `action-item-${item.id}`,
        });
        markNotified(item.id);
      }
    }
  }, [data]);
}
