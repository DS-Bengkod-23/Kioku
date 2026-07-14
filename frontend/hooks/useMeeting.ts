import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getMeeting,
  updateMeeting,
  deleteMeeting,
  updateAttendance,
  completeMeeting,
  lockAttendance,
  confirmCheckin,
} from "@/lib/api";

export function useMeeting(id: string) {
  return useQuery({
    queryKey: ["meeting", id],
    queryFn: () => getMeeting(id),
    enabled: !!id,
  });
}

export function useUpdateMeeting(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Parameters<typeof updateMeeting>[1]) =>
      updateMeeting(id, data),
    onSuccess: (updatedMeeting) => {
      queryClient.setQueryData(["meeting", id], updatedMeeting);
      queryClient.invalidateQueries({ queryKey: ["meetings"] });
    },
  });
}

export function useCompleteMeeting(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => completeMeeting(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["meeting", id] });
      queryClient.invalidateQueries({ queryKey: ["meetings"] });
    },
  });
}

export function useLockAttendance(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => lockAttendance(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["meeting", id] });
    },
  });
}

export function useDeleteMeeting() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteMeeting,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["meetings"] });
    },
  });
}

export function useUpdateAttendance(meetingId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      participantId,
      status,
    }: {
      participantId: string;
      status: "pending" | "hadir" | "tidak_hadir";
    }) => updateAttendance(meetingId, participantId, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["meeting", meetingId] });
    },
  });
}

// Presensi mandiri oleh peserta yang login lewat akunnya sendiri, dengan menggunakan
// checkin_token milik mereka sendiri (dari participants[]) — reuse endpoint check-in
// yang sama dengan portal magic-link, jadi tidak perlu endpoint backend baru.
export function useSelfCheckIn(meetingId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (checkinToken: string) => confirmCheckin(checkinToken),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["meeting", meetingId] });
    },
  });
}
