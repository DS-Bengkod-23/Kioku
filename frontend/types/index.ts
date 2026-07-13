// Tipe-tipe ini mengikuti kontrak response backend yang sesungguhnya
// (lihat backend/app/schemas/meeting.py, action_item.py, recording.py).

export type MeetingStatus = "scheduled" | "completed" | "cancelled";
export type AttendanceStatus = "pending" | "hadir" | "tidak_hadir";
export type ActionItemStatus = "open" | "done";
export type ParticipantRole = "organizer" | "peserta";
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

export interface UserProfile {
  id: string;
  name: string;
  email: string;
  job_title: string | null;
  department: string | null;
  bio: string | null;
  created_at: string;
}
