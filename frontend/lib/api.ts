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
  // TODO: aktifkan setelah backend tambahkan field "user" ke login response
  // if (response.data.user) {
  //   localStorage.setItem("user_profile", JSON.stringify(response.data.user));
  // }
  return response.data;
};

export const registerUser = async (data: { name: string; email: string; password: string }) => {
  const response = await api.post("/auth/register", data);
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

export const searchMeetings = async (q: string, params?: { page?: number; limit?: number }) => {
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
  a.click();
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
  a.click();
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
  payload: { status?: "open" | "done"; assignee_participant_id?: string | null }
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

export default api;
