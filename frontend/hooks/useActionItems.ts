import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getMyActionItems, updateActionItem, createActionItem } from "@/lib/api";

export function useMyActionItems(status?: "open" | "done") {
  return useQuery({
    queryKey: ["action-items", status],
    queryFn: () => getMyActionItems(status),
  });
}

export function useUpdateActionItem(meetingId?: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      status,
      assigneeId,
    }: {
      id: string;
      status?: "open" | "done";
      assigneeId?: string | null;
    }) => updateActionItem(id, { status, assignee_participant_id: assigneeId }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["action-items"] });
      if (meetingId) {
        queryClient.invalidateQueries({ queryKey: ["meeting", meetingId] });
      }
    },
  });
}

export function useCreateActionItem(meetingId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: { task: string; assignee_participant_id?: string | null; due_date?: string | null }) =>
      createActionItem(meetingId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["meeting", meetingId] });
    },
  });
}
