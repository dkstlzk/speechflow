export type ProcessingStatus =
  | "idle"
  | "uploading"
  | "processing"
  | "completed"
  | "failed";

export type TranscriptType =
  | "meeting"
  | "conversation"
  | "interview"
  | "lecture"
  | "presentation";

export interface Session {
  id: string;
  createdAt: string;
  status: ProcessingStatus;
  transcriptType: TranscriptType;
  fileName?: string;
  durationSec?: number;
}

export interface TranscriptSegment {
  speaker: string;
  text: string;
  startSec?: number;
  endSec?: number;
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
  completed?: boolean;
}

export interface ApiResponse<T> {
  data: T;
  ok: boolean;
  message?: string;
}

export type ConnectionStatus = "connected" | "connecting" | "disconnected";
export type RecordingStatus =
  | "idle"
  | "recording"
  | "paused"
  | "processing"
  | "completed";

export interface StreamingEvent {
  id: string;
  timestamp: string;
  type: string;
  message: string;
}
