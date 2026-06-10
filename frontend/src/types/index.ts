export type ProcessingStatus =
  | "idle"
  | "uploading"
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
  fileName?: string;
  durationSec?: number;
  title?: string;
  has_audio?: boolean;
  audio_url?: string;
}

export interface TranscriptSegment {
  speaker: string;
  text: string;

  chunk_index?: number;

  startSec?: number;
  endSec?: number;

  is_partial?: boolean;
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
}

export interface ActionItem {
  id: string;
  text: string;
  owner?: string;
  dueDate?: string;
}

export interface ApiResponse<T> {
  data: T;
  ok: boolean;
  message?: string;
}

export type ConnectionStatus = "connected" | "connecting" | "disconnected";
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
