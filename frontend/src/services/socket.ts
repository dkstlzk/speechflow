/**
 * Mock socket service. Replace internals with Socket.IO client later.
 * Components must only consume this abstraction.
 */
import type { StreamingEvent, TranscriptSegment } from "@/types";

type TranscriptListener = (chunk: TranscriptSegment) => void;
type StatusListener = (event: StreamingEvent) => void;

let connected = false;
let recording = false;
let transcriptListeners: TranscriptListener[] = [];
let statusListeners: StatusListener[] = [];
let mockInterval: ReturnType<typeof setInterval> | null = null;

const MOCK_LINES: TranscriptSegment[] = [
  { speaker: "Participant A", text: "Hello everyone, thanks for joining." },
  { speaker: "Participant B", text: "Glad to be here." },
  { speaker: "Participant A", text: "Today we'll review attendance issues from last week." },
  { speaker: "Participant C", text: "I have some data prepared on that." },
  { speaker: "Participant B", text: "Let's go through it step by step." },
  { speaker: "Participant A", text: "Sounds good. Please share your screen." },
];

function emitEvent(type: string, message: string) {
  const ev: StreamingEvent = {
    id: Math.random().toString(36).slice(2),
    timestamp: new Date().toISOString(),
    type,
    message,
  };
  statusListeners.forEach((l) => l(ev));
}

export async function connect(): Promise<void> {
  emitEvent("connecting", "Establishing connection");
  await new Promise((r) => setTimeout(r, 400));
  connected = true;
  emitEvent("connected", "Socket connected");
}

export function disconnect(): void {
  stopRecording();
  connected = false;
  emitEvent("disconnected", "Socket disconnected");
  transcriptListeners = [];
  statusListeners = [];
}

export function isConnected() {
  return connected;
}

export function startRecording(sessionId: string): void {
  if (!connected) return;
  recording = true;
  emitEvent("session_started", `Session ${sessionId} started`);
  let i = 0;
  mockInterval = setInterval(() => {
    if (!recording) return;
    emitEvent("audio_chunk_sent", `Audio chunk #${i + 1} sent`);
    const line = MOCK_LINES[i % MOCK_LINES.length];
    transcriptListeners.forEach((l) => l(line));
    emitEvent("transcript_chunk_received", "Transcript chunk received");
    i++;
  }, 2500);
}

export function stopRecording(): void {
  if (mockInterval) {
    clearInterval(mockInterval);
    mockInterval = null;
  }
  if (recording) {
    recording = false;
    emitEvent("session_finalized", "Session finalized");
  }
}

export function sendAudioChunk(_chunk: ArrayBuffer): void {
  // Placeholder. Real impl pipes chunks to socket.
}

export function subscribeToTranscript(cb: TranscriptListener): () => void {
  transcriptListeners.push(cb);
  return () => {
    transcriptListeners = transcriptListeners.filter((l) => l !== cb);
  };
}

export function subscribeToStatus(cb: StatusListener): () => void {
  statusListeners.push(cb);
  return () => {
    statusListeners = statusListeners.filter((l) => l !== cb);
  };
}
