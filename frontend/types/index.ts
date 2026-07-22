// Tipe-tipe ini mengikuti kontrak response backend yang sesungguhnya
// (lihat backend/app/schemas/meeting.py, action_item.py, recording.py).

export type MeetingStatus = "scheduled" | "completed" | "cancelled";
export type AttendanceStatus = "pending" | "hadir" | "tidak_hadir";
// Belum ada di backend — lihat plan/handoff-avatar-rsvp.md. Ini konfirmasi
// "akan hadir/tidak" SEBELUM rapat, beda dari AttendanceStatus yang nyatet
// kehadiran beneran pas hari-H (lewat check-in).
export type RsvpStatus = "pending" | "akan_hadir" | "tidak_hadir";
export type ActionItemStatus = "open" | "done";
export type ParticipantRole = "organizer" | "peserta";
// Role level aplikasi (beda dari ParticipantRole yang per-meeting). Sesuai
// plan/admin-role-frontend-handoff.md — GET /auth/me sekarang balikin field ini.
export type AppRole = "user" | "admin" | "superadmin";
export type ProcessingStatus =
  | "queued"
  | "transcribing"
  | "diarizing"
  | "extracting"
  | "sending_email"
  | "completed"
  | "failed";

export interface ParticipantResponse {
  id: string;
  email: string;
  name: string | null;
  role: ParticipantRole;
  attendance_status: AttendanceStatus;
  checkin_token: string | null;
  // Belum ada di backend — lihat plan/handoff-avatar-rsvp.md.
  rsvp_status?: RsvpStatus;
}

export interface OrganizerResponse {
  id: string;
  name: string;
  email: string;
}

export interface RecordingResponse {
  id: string;
  file_url: string;
  duration: number | null;
  size: number;
  uploaded_at: string;
  processing_status: ProcessingStatus;
}

export interface ProcessingStatusResponse {
  processing_status: ProcessingStatus;
  steps: Record<string, string> | null;
  error: string | null;
}

export interface TranscriptSegment {
  speaker: string;
  start: number;
  end: number;
  text: string;
}

export interface TranscriptDTO {
  id: string;
  segments: TranscriptSegment[];
}

export interface SummaryDTO {
  id: string;
  tldr: string;
  decisions: string[];
  topics: string[];
}

export interface AssigneeDTO {
  id: string;
  name: string;
  email: string;
}

export interface ActionItemDTO {
  id: string;
  task: string;
  assignee_participant_id: string | null;
  assignee: AssigneeDTO | null;
  due_date: string | null;
  status: ActionItemStatus;
}

export interface MeetingListItem {
  id: string;
  title: string;
  scheduled_at: string;
  location: string | null;
  status: MeetingStatus;
  participant_count: number;
  attendance_count: number;
  has_recording: boolean;
  processing_status: ProcessingStatus | null;
  // Additive, dari plan/admin-role-frontend-handoff.md — null kalau belum
  // di-soft-delete admin.
  deleted_at?: string | null;
}

export interface MeetingListResponse {
  items: MeetingListItem[];
  total: number;
  page: number;
  limit: number;
}

export interface MeetingDetail {
  id: string;
  title: string;
  scheduled_at: string;
  location: string | null;
  location_building: string | null;
  location_room: string | null;
  location_city: string | null;
  description: string | null;
  agenda_text: string | null;
  status: MeetingStatus;
  duration_minutes: number;
  attendance_locked: boolean;
  organizer: OrganizerResponse;
  participants: ParticipantResponse[];
  recording: RecordingResponse | null;
  processing_status: ProcessingStatus | null;
  transcript: TranscriptDTO | null;
  summary: SummaryDTO | null;
  action_items: ActionItemDTO[] | null;
}

// GET /meetings/{id} sekarang bisa balikin bentuk ini kalau meeting di-soft-delete
// admin — lihat plan/admin-role-frontend-handoff.md bagian "Efek soft-delete".
// HARUS dicek ("deleted" in response) sebelum baca field MeetingDetail lainnya.
export interface MeetingDeletedNotice {
  id: string;
  deleted: true;
  message: string;
}

export type MeetingDetailOrNotice = MeetingDetail | MeetingDeletedNotice;

export interface MeetingSimple {
  id: string;
  title: string;
  scheduled_at: string;
}

export interface MyActionItem {
  id: string;
  task: string;
  due_date: string | null;
  status: ActionItemStatus;
  meeting: MeetingSimple;
}

export interface CalendarStatusResponse {
  connected: boolean;
  connected_at: string | null;
}

export interface UserProfile {
  id: string;
  name: string;
  email: string;
  job_title: string | null;
  department: string | null;
  bio: string | null;
  created_at: string;
  // Belum ada di backend — lihat plan/handoff-avatar-rsvp.md.
  avatar_url?: string | null;
  // Sesuai plan/admin-role-frontend-handoff.md — default "user" kalau field ini
  // belum dikirim BE (mis. sebelum kodenya beneran live), biar guard admin aman
  // gagal ke arah "bukan admin", bukan malah nampilin akses ke semua orang.
  role?: AppRole;
}

// ==========================================
// ADMIN & SUPERADMIN
// Belum ada di backend — lihat plan/admin-role-frontend-handoff.md.
// ==========================================

export interface UserAdminResponse {
  id: string;
  name: string;
  email: string;
  role: AppRole;
  suspended_at: string | null;
  created_at: string;
}

export interface MeetingAdminParticipant {
  name: string | null;
  email: string;
  role: ParticipantRole;
  attendance_status: string | null;
}

export interface MeetingAdminResponse {
  id: string;
  title: string;
  scheduled_at: string;
  status: string;
  organizer_name: string;
  organizer_email: string;
  participants: MeetingAdminParticipant[];
  action_items: { open: number; done: number };
}

export interface MeetingContentAccessResponse {
  meeting_id: string;
  transcript_segments: TranscriptSegment[] | null;
  summary_tldr: string | null;
  summary_decisions: string[] | null;
  summary_topics: string[] | null;
}

export type AuditLogAction =
  | "suspend_user"
  | "unsuspend_user"
  | "promote_user"
  | "demote_user"
  | "reset_password"
  | "request_meeting_access"
  | "delete_meeting"
  | "delete_recording";

export interface AuditLogResponse {
  id: string;
  actor_id: string | null;
  action: AuditLogAction;
  target_type: string;
  target_id: string;
  reason: string | null;
  created_at: string;
}
