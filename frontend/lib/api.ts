import axios from "axios";

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1",
  headers: {
    "Content-Type": "application/json",
  },
});

// Attach JWT token ke setiap request
api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("access_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

// Jika 401, hapus token dan redirect ke login
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && typeof window !== "undefined") {
      localStorage.removeItem("access_token");
      localStorage.removeItem("user_profile");
      document.cookie = "access_token=; path=/; max-age=0";
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

// ==========================================
// AUTH
// ==========================================

export const loginUser = async (credentials: { email: string; password: string }) => {
  const response = await api.post("/auth/login", credentials);
  const { access_token } = response.data;
  localStorage.setItem("access_token", access_token);
  // Set cookie agar middleware bisa baca
  document.cookie = `access_token=${access_token}; path=/; max-age=${7 * 24 * 60 * 60}`;
  return response.data;
};

export const registerUser = async (data: { name: string; email: string; password: string }) => {
  const response = await api.post("/auth/register", data);
  return response.data;
};

export const getProfile = async () => {
  const response = await api.get("/auth/me");
  return response.data;
};

export const updateProfile = async (data: {
  name?: string;
  email?: string;
  job_title?: string | null;
  department?: string | null;
  bio?: string | null;
}) => {
  const response = await api.patch("/auth/me", data);
  return response.data;
};

// Belum ada di backend — lihat plan/handoff-avatar-rsvp.md. Diasumsikan balikin
// UserProfile lengkap (termasuk avatar_url baru) supaya react-query cache bisa
// langsung di-update dari response ini, gak perlu refetch terpisah.
export const uploadAvatar = async (file: File) => {
  const formData = new FormData();
  formData.append("file", file);
  const response = await api.post("/auth/me/avatar", formData, {
    headers: { "Content-Type": undefined },
  });
  return response.data;
};

export const deleteAvatar = async () => {
  const response = await api.delete("/auth/me/avatar");
  return response.data;
};

// Login/register lewat Google SSO — bentuk response HARUS sama dengan loginUser()
// di atas (access_token + name), plus email (loginUser tidak butuh ini karena FE
// sudah punya email dari input form; alur Google tidak punya sumber lain buat email).
// Lihat plan/handoff-google-integration.md — endpoint ini belum ada di backend,
// panggilan ini akan 404 sampai BE mengimplementasikan POST /auth/google.
export const loginWithGoogle = async (idToken: string) => {
  const response = await api.post("/auth/google", { id_token: idToken });
  const { access_token } = response.data;
  localStorage.setItem("access_token", access_token);
  document.cookie = `access_token=${access_token}; path=/; max-age=${7 * 24 * 60 * 60}`;
  return response.data;
};

export const logoutUser = () => {
  localStorage.removeItem("access_token");
  localStorage.removeItem("user_profile");
  document.cookie = "access_token=; path=/; max-age=0";
  window.location.href = "/login";
};

// ==========================================
// MEETINGS
// ==========================================

export interface MeetingsParams {
  page?: number;
  limit?: number;
  status?: "scheduled" | "completed" | "cancelled";
  date_from?: string;
  date_to?: string;
}

export const getMeetings = async (params?: MeetingsParams) => {
  const response = await api.get("/meetings", { params });
  return response.data;
};

export const getMeeting = async (id: string) => {
  const response = await api.get(`/meetings/${id}`);
  return response.data;
};

export const createMeeting = async (data: {
  title: string;
  scheduled_at: string;
  location?: string;
  location_building?: string;
  location_room?: string;
  location_city?: string;
  description?: string;
  agenda_text?: string;
  participant_emails: string[];
  duration_minutes?: number;
}) => {
  const response = await api.post("/meetings", data);
  return response.data;
};

export const updateMeeting = async (
  id: string,
  data: {
    title?: string;
    scheduled_at?: string;
    location?: string;
    location_building?: string;
    location_room?: string;
    location_city?: string;
    description?: string;
    agenda_text?: string;
    participant_emails?: string[];
    duration_minutes?: number;
  }
) => {
  const response = await api.patch(`/meetings/${id}`, data);
  return response.data;
};

export const deleteMeeting = async (id: string) => {
  await api.delete(`/meetings/${id}`);
};

export const completeMeeting = async (id: string) => {
  const response = await api.patch(`/meetings/${id}/complete`);
  return response.data;
};

export const searchMeetings = async (
  q: string,
  params?: { page?: number; limit?: number; date_from?: string; date_to?: string }
) => {
  const response = await api.get("/meetings/search", { params: { q, ...params } });
  return response.data;
};

// ==========================================
// RECORDINGS
// ==========================================

export const uploadRecording = async (
  meetingId: string,
  formData: FormData,
  onUploadProgress?: (percent: number) => void
) => {
  const response = await api.post(`/meetings/${meetingId}/recording`, formData, {
    onUploadProgress: (event) => {
      if (!onUploadProgress || !event.total) return;
      onUploadProgress(Math.round((event.loaded / event.total) * 100));
    },
    headers: { "Content-Type": undefined },
  });
  return response.data;
};

export const getRecordingStatus = async (meetingId: string) => {
  const response = await api.get(`/meetings/${meetingId}/recording/status`);
  return response.data;
};

export const deleteRecording = async (meetingId: string) => {
  await api.delete(`/meetings/${meetingId}/recording`);
};

// Belum ada di backend — lihat plan/handoff-audio-playback-reminder.md.
// file_url di RecordingResponse cuma object key MinIO mentah, bukan URL yang bisa
// diakses langsung, jadi <audio src> gak bisa dipasangin ke situ. Endpoint ini
// diasumsikan balikin bytes audio mentah (bukan JSON) di belakang auth Bearer yang
// sama kayak endpoint lain — makanya diambil sebagai blob lalu dikonversi ke object
// URL lokal, pola yang sama dengan downloadNotulenPdf() di atas.
export const getRecordingAudioBlobUrl = async (meetingId: string): Promise<string> => {
  const response = await api.get(`/meetings/${meetingId}/recording/audio`, {
    responseType: "blob",
  });
  return URL.createObjectURL(response.data);
};

// ==========================================
// CHECK-IN (Public, No Auth)
// ==========================================

export const getCheckin = async (token: string) => {
  const response = await api.get(`/check-in/${token}`);
  return response.data;
};

export const confirmCheckin = async (token: string) => {
  const response = await api.post(`/check-in/${token}/confirm`);
  return response.data;
};

export const updateCheckinActionItem = (
  token: string,
  actionItemId: string,
  status: "open" | "done"
) => api.patch(`/check-in/${token}/action-items/${actionItemId}`, { status }).then((r) => r.data);

export const downloadCheckinNotulenPdf = async (token: string, meetingTitle: string) => {
  const response = await api.get(`/check-in/${token}/notulen.pdf`, {
    responseType: "blob",
  });
  const url = URL.createObjectURL(response.data);
  const a = document.createElement("a");
  a.href = url;
  a.download = `notulen-${meetingTitle}.pdf`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
};

export const downloadNotulenPdf = async (meetingId: string, meetingTitle: string) => {
  const response = await api.get(`/meetings/${meetingId}/notulen.pdf`, {
    responseType: "blob",
  });
  const url = URL.createObjectURL(response.data);
  const a = document.createElement("a");
  a.href = url;
  a.download = `notulen-${meetingTitle}.pdf`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
};

// ==========================================
// ATTENDANCE
// ==========================================

export const updateAttendance = async (
  meetingId: string,
  participantId: string,
  status: "pending" | "hadir" | "tidak_hadir"
) => {
  const response = await api.patch(
    `/meetings/${meetingId}/participants/${participantId}/attendance`,
    { status }
  );
  return response.data;
};

export const lockAttendance = async (meetingId: string) => {
  const response = await api.patch(`/meetings/${meetingId}/attendance/lock`);
  return response.data;
};

// Belum ada di backend — lihat plan/handoff-avatar-rsvp.md. Self-service oleh
// participant yang login (current_user), beda dari updateAttendance() di atas
// yang dipakai ORGANIZER buat nyatet kehadiran orang lain pas hari-H.
export const submitRsvp = async (meetingId: string, response_: "akan_hadir" | "tidak_hadir") => {
  const response = await api.patch(`/meetings/${meetingId}/rsvp`, { response: response_ });
  return response.data;
};

// ==========================================
// ACTION ITEMS
// ==========================================

export const getMyActionItems = async (status?: "open" | "done") => {
  const response = await api.get("/me/action-items", {
    params: status ? { status } : undefined,
  });
  return response.data;
};

export const updateActionItem = async (
  id: string,
  payload: { status?: "open" | "done"; assignee_participant_id?: string | null; due_date?: string | null }
) => {
  const response = await api.patch(`/action-items/${id}`, payload);
  return response.data;
};

export const createActionItem = async (
  meetingId: string,
  data: { task: string; assignee_participant_id?: string | null; due_date?: string | null }
) => {
  const response = await api.post(`/meetings/${meetingId}/action-items`, data);
  return response.data;
};

// ==========================================
// GOOGLE CALENDAR SYNC
// Belum ada di backend — endpoint sesuai plan/handoff-google-integration.md,
// akan 404 sampai BE mengimplementasikannya. FE dibangun duluan (parallel dev),
// nanti di-debug bareng begitu BE siap.
// ==========================================

export const getCalendarStatus = async () => {
  const response = await api.get("/me/calendar-status");
  return response.data;
};

export const disconnectCalendar = async () => {
  const response = await api.delete("/auth/google/calendar");
  return response.data;
};

// Bukan panggilan axios — ini cuma redirect penuh ke backend (OAuth consent screen),
// jadi cukup bangun URL-nya, konsumennya pakai window.location.href langsung.
export const getGoogleCalendarConnectUrl = () => {
  const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
  return `${base}/auth/google/calendar/connect`;
};

// ==========================================
// ADMIN & SUPERADMIN
// Kontrak dari plan/admin-role-frontend-handoff.md (Audi, 2026-07-20) — status
// kode BE-nya di GitHub belum terkonfirmasi ada saat ini, jadi endpoint-endpoint
// ini kemungkinan 404 sampai dikonfirmasi/di-merge. Dibangun duluan (parallel
// dev) sesuai pola yang sama dengan fitur-fitur sebelumnya.
// ==========================================

export const getAdminUsers = async () => {
  const response = await api.get("/admin/users");
  return response.data;
};

export const suspendUser = async (userId: string) => {
  const response = await api.patch(`/admin/users/${userId}/suspend`);
  return response.data;
};

export const unsuspendUser = async (userId: string) => {
  const response = await api.patch(`/admin/users/${userId}/unsuspend`);
  return response.data;
};

export const updateUserRole = async (userId: string, role: "user" | "admin" | "superadmin") => {
  const response = await api.patch(`/admin/users/${userId}/role`, { role });
  return response.data;
};

export const resetUserPassword = async (userId: string) => {
  const response = await api.post(`/admin/users/${userId}/reset-password`);
  return response.data;
};

export const getAdminMeetings = async () => {
  const response = await api.get("/admin/meetings");
  return response.data;
};

// Setiap panggilan = 1 baris audit log baru di BE (by design, lihat handoff doc)
// — JANGAN cache/reuse hasil ini, selalu request baru tiap kali admin buka isi
// meeting, walau meeting yang sama.
export const requestMeetingAccess = async (meetingId: string, reason: string) => {
  const response = await api.post(`/admin/meetings/${meetingId}/access-requests`, { reason });
  return response.data;
};

export const adminDeleteMeeting = async (meetingId: string) => {
  await api.delete(`/admin/meetings/${meetingId}`);
};

export const adminDeleteRecording = async (recordingId: string) => {
  await api.delete(`/admin/recordings/${recordingId}`);
};

export const getAuditLogs = async (limit = 50, offset = 0) => {
  const response = await api.get("/admin/audit-logs", { params: { limit, offset } });
  return response.data;
};

// Publik, tanpa auth — dipanggil dari halaman /reset-password/[token].
export const confirmResetPassword = async (token: string, newPassword: string) => {
  const response = await api.post("/auth/reset-password/confirm", {
    token,
    new_password: newPassword,
  });
  return response.data;
};

export default api;
