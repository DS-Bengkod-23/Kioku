import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getMyActionItems, updateActionItem } from "@/lib/api";

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
