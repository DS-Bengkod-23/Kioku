import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getMeetings, createMeeting, searchMeetings, type MeetingsParams } from "@/lib/api";

export function useMeetings(params?: MeetingsParams, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ["meetings", params],
    queryFn: () => getMeetings(params),
    enabled: options?.enabled ?? true,
  });
}

export function useSearchMeetings(
  q: string,
  params?: { page?: number; limit?: number; date_from?: string; date_to?: string }
) {
  return useQuery({
    queryKey: ["meetings", "search", q, params],
    queryFn: () => searchMeetings(q, params),
    enabled: q.trim().length > 0,
  });
}

export function useCreateMeeting() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createMeeting,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["meetings"] });
    },
  });
}
