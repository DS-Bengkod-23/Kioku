import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getMeeting,
  updateMeeting,
  deleteMeeting,
  updateAttendance,
  completeMeeting,
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
