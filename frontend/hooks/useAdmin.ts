import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getAdminUsers,
  suspendUser,
  unsuspendUser,
  updateUserRole,
  resetUserPassword,
  getAdminMeetings,
  requestMeetingAccess,
  adminDeleteMeeting,
  adminDeleteRecording,
  getAuditLogs,
} from "@/lib/api";

// Semua hook di file ini konsumsi kontrak plan/admin-role-frontend-handoff.md —
// belum terkonfirmasi ada di backend, lihat catatan di lib/api.ts.

export function useAdminUsers() {
  return useQuery({
    queryKey: ["admin-users"],
    queryFn: getAdminUsers,
  });
}

export function useSuspendUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: suspendUser,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-users"] }),
  });
}

export function useUnsuspendUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: unsuspendUser,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-users"] }),
  });
}

export function useUpdateUserRole() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: "user" | "admin" | "superadmin" }) =>
      updateUserRole(userId, role),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-users"] }),
  });
}

export function useResetUserPassword() {
  return useMutation({
    mutationFn: resetUserPassword,
  });
}

export function useAdminMeetings() {
  return useQuery({
    queryKey: ["admin-meetings"],
    queryFn: getAdminMeetings,
  });
}

// Sengaja bukan useQuery — tiap panggilan harus jadi request baru (audit log baru
// di BE tiap kali), jadi gak boleh di-cache/reuse hasil sebelumnya sama sekali.
export function useRequestMeetingAccess() {
  return useMutation({
    mutationFn: ({ meetingId, reason }: { meetingId: string; reason: string }) =>
      requestMeetingAccess(meetingId, reason),
  });
}

export function useAdminDeleteMeeting() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: adminDeleteMeeting,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-meetings"] }),
  });
}

export function useAdminDeleteRecording() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: adminDeleteRecording,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-meetings"] }),
  });
}

export function useAuditLogs(limit = 50, offset = 0) {
  return useQuery({
    queryKey: ["admin-audit-logs", limit, offset],
    queryFn: () => getAuditLogs(limit, offset),
  });
}
