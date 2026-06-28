export type ProcessingStatus =
  | "idle"
  | "pending"
  | "uploading"
  | "preprocessing"
  | "transcribing"
  | "diarizing"
  | "processing"
  | "completed"
  | "failed"
  | "recording"
  | "finalizing";

export type TranscriptType =
  | "meeting"
  | "conversation"
  | "interview"
  | "lecture"
  | "presentation"
  | "voice_note"
  | "unknown";

export interface Session {
  id: string;
  createdAt: string;
  status: ProcessingStatus;
  transcriptType?: TranscriptType;
  active_job_type?: string | null;
  fileName?: string;
  durationSec?: number;
  title?: string;
  host_name?: string;
  participants?: string;
  has_audio?: boolean;
  audio_url?: string;
  diarization_mode?: string;
  diarized_at: string | null;
  detected_language: string | null;
  detected_languages: { code: string; percentage: number }[] | null;
  processing_stage?: string;
}

export interface TranscriptSegment {
  speaker: string;
  displayName?: string;
  text: string;
  id?: number;

  chunk_index?: number;

  startSec?: number;
  endSec: number;
  is_partial?: boolean;
  language?: string | null;
  sessionId?: string;
}

export interface TranscriptResponse {
  sessionId: string;
  segments: TranscriptSegment[];
  rawText: string;
}

export interface SummaryResponse {
  sessionId: string;
  summary: string;
  mom: string | null;
  history?: {
    iteration: number;
    summary: string;
    mom: string | null;
    created_at: string | null;
  }[];
}

export interface ActionItem {
  id: string;
  text: string;
  owner?: string;
  dueDate?: string;
  iteration?: number;
}

export interface ApiResponse<T> {
  data: T;
  ok: boolean;
  message?: string;
}

export type ConnectionStatus = "connected" | "connecting" | "disconnected" | "error";
export type RecordingStatus = "idle" | "recording" | "paused" | "finalizing" | "completed";
export type MicrophoneState =
  | "initializing"
  | "not_requested"
  | "ready"
  | "recording"
  | "paused"
  | "denied";

export interface StreamingEvent {
  id: string;
  timestamp: string;
  type: string;
  message: string;
  sessionId?: string;
}

export interface CaptionUpdate {
  text: string;
  timestamp: number;
  sessionId?: string;
}
