import { useEffect, useRef, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { uploadRecording, getRecordingStatus, deleteRecording } from "@/lib/api";

const DONE_STATUSES = ["completed", "failed"];
// Batas atas polling: kalau setelah durasi ini status belum juga completed/failed
// (worker crash, task hilang, dll), berhenti polling. Tanpa ini, kalau backend tidak
// pernah lagi meng-update status, UI polling tiap 3 detik selamanya tanpa ada sinyal
// ke user bahwa sesuatu janggal.
const MAX_POLLING_MS = 60 * 60 * 1000; // 1 jam

export function useRecordingStatus(meetingId: string, enabled = false) {
  const queryClient = useQueryClient();
  const pollStartRef = useRef<number | null>(null);
  if (enabled) {
    if (pollStartRef.current === null) pollStartRef.current = Date.now();
  } else {
    pollStartRef.current = null;
  }

  const query = useQuery({
    queryKey: ["recording-status", meetingId],
    queryFn: () => getRecordingStatus(meetingId),
    enabled: enabled && !!meetingId,
    // Poll setiap 3 detik, berhenti otomatis jika sudah selesai, gagal, atau sudah
    // melewati MAX_POLLING_MS tanpa kunjung selesai.
    refetchInterval: (q) => {
      const status = q.state.data?.processing_status;
      if (status && DONE_STATUSES.includes(status)) return false;
      if (pollStartRef.current && Date.now() - pollStartRef.current > MAX_POLLING_MS) {
        return false;
      }
      return 3000;
    },
  });

  const status = query.data?.processing_status;

  // Query ["meeting", meetingId] (isi summary/transcript) gak otomatis ke-refetch
  // pas polling ini berhenti — tanpa ini, begitu processing "completed", summary
  // dan transkrip yang harusnya udah ada tetap gak muncul sampai user refresh
  // manual, karena data meeting yang lama masih dianggap valid oleh react-query.
  useEffect(() => {
    if (status && DONE_STATUSES.includes(status)) {
      queryClient.invalidateQueries({ queryKey: ["meeting", meetingId] });
    }
  }, [status, meetingId, queryClient]);
  const isStalled =
    enabled &&
    !!pollStartRef.current &&
    Date.now() - pollStartRef.current > MAX_POLLING_MS &&
    !(status && DONE_STATUSES.includes(status));

  return { ...query, isStalled };
}

export function useUploadRecording(meetingId: string) {
  const queryClient = useQueryClient();
  const [progress, setProgress] = useState(0);

  const mutation = useMutation({
    mutationFn: (formData: FormData) => {
      setProgress(0);
      return uploadRecording(meetingId, formData, setProgress);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["meeting", meetingId] });
      queryClient.invalidateQueries({ queryKey: ["recording-status", meetingId] });
    },
    onSettled: () => {
      setProgress(0);
    },
  });

  return { ...mutation, progress: mutation.isPending ? progress : 0 };
}

export function useDeleteRecording(meetingId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => deleteRecording(meetingId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["meeting", meetingId] });
      queryClient.removeQueries({ queryKey: ["recording-status", meetingId] });
    },
  });
}
