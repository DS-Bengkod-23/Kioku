import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getCalendarStatus, disconnectCalendar } from "@/lib/api";

export function useCalendarStatus() {
  return useQuery({
    queryKey: ["calendar-status"],
    queryFn: getCalendarStatus,
    // Endpoint belum ada di BE (lihat plan/handoff-google-integration.md) — gagal cepat
    // ke isError daripada retry berkali-kali ke 404 yang sama.
    retry: false,
  });
}

export function useDisconnectCalendar() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: disconnectCalendar,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["calendar-status"] });
    },
  });
}
