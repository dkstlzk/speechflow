/**
 * Socket.IO client abstraction for SpeechFlow realtime pipeline.
 *
 * Two separate event channels:
 *   - caption_update  → disposable live captions (UI only)
 *   - transcript_committed → finalized chunks (persisted in DB)
 *
 * Components must only consume this abstraction.
 */
import { io, Socket } from "socket.io-client";
import type { CaptionUpdate, StreamingEvent, TranscriptSegment } from "@/types";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:5000";

export const socket: Socket = io(API_URL, {
  autoConnect: false,
  transports: ["websocket"],
});

type TranscriptListener = (chunk: TranscriptSegment) => void;
type CaptionListener = (caption: CaptionUpdate) => void;
type StatusListener = (event: StreamingEvent) => void;

let transcriptListeners: TranscriptListener[] = [];
let captionListeners: CaptionListener[] = [];
let statusListeners: StatusListener[] = [];

function emitStatus(type: string, message: string, sessionId?: string) {
  const ev: StreamingEvent = {
    id: Math.random().toString(36).slice(2),
    timestamp: new Date().toISOString(),
    type,
    message,
    sessionId,
  };
  statusListeners.forEach((l) => l(ev));
}

// ── Connection Events ──────────────────────────────────────────────

socket.on("connect", () => {
  emitStatus("connected", "Socket connected");
});

socket.on("disconnect", () => {
  emitStatus("disconnected", "Socket disconnected");
});

socket.on("connect_error", (err) => {
  emitStatus("error", `Connection error: ${err.message}`);
});

socket.on("stream_ack", (data) => {
  emitStatus("stream_started", "Backend acknowledged stream start", data?.session_id ? String(data.session_id) : undefined);
});

socket.on("stream_complete", (data) => {
  emitStatus("stream_complete", "Backend finalized stream", data?.session_id ? String(data.session_id) : undefined);
});

socket.on("stream_finalized", (data) => {
  emitStatus("stream_finalized", "All segments persisted — session ready", data?.session_id ? String(data.session_id) : undefined);
});

socket.on("stream_paused", (data) => {
  emitStatus("stream_paused", "Recording paused", data?.session_id ? String(data.session_id) : undefined);
});

socket.on("stream_resumed", (data) => {
  emitStatus("stream_resumed", "Recording resumed", data?.session_id ? String(data.session_id) : undefined);
});

// ── Caption Channel (disposable, UI only) ──────────────────────────

socket.on("caption_update", (data) => {
  const caption: CaptionUpdate = {
    text: data.text || "",
    timestamp: data.timestamp || Date.now() / 1000,
    sessionId: data.session_id ? String(data.session_id) : undefined,
  };
  captionListeners.forEach((l) => l(caption));
});

// ── Transcript Channel (committed, persisted) ──────────────────────

socket.on("transcript_committed", (data) => {
  const segment: TranscriptSegment = {
    speaker: data.speaker || "UNKNOWN",
    text: data.text || "",
    startSec: data.start_time,
    endSec: data.end_time,
    chunk_index: data.chunk_index,
    is_partial: false,
    sessionId: data.session_id ? String(data.session_id) : undefined,
  };
  transcriptListeners.forEach((l) => l(segment));
});

// ── Connection Control ─────────────────────────────────────────────

export async function connect(): Promise<void> {
  emitStatus("connecting", "Establishing connection...");

  if (socket.connected) {
    emitStatus("connected", "Socket already connected");
    return;
  }

  await new Promise<void>((resolve, reject) => {
    let timeout: ReturnType<typeof setTimeout>;

    const onConnect = () => {
      clearTimeout(timeout);
      socket.off("connect_error", onConnectError);
      resolve();
    };

    const onConnectError = (err: any) => {
      clearTimeout(timeout);
      socket.off("connect", onConnect);
      reject(err);
    };

    timeout = setTimeout(() => {
      socket.off("connect", onConnect);
      socket.off("connect_error", onConnectError);
      reject(new Error("Socket connection timeout"));
    }, 5000);

    socket.once("connect", onConnect);
    socket.once("connect_error", onConnectError);

    socket.connect();
  });
}

export function disconnect(): void {
  if (socket.connected) {
    socket.disconnect();
  }
}

export function isConnected(): boolean {
  return socket.connected;
}

// ── Recording Control ──────────────────────────────────────────────

export function startRecording(sessionId: string): void {
  if (!socket.connected) return;

  emitStatus("session_started", `Session ${sessionId} started`);

  socket.emit("stream_start", {
    session_id: sessionId,
  });
}

export function stopRecording(): void {
  if (!socket.connected) return;

  socket.emit("stream_end", {});

  emitStatus("session_finalized", "Session finalized");
}

export function pauseRecording(): void {
  if (!socket.connected) return;
  socket.emit("stream_pause", {});
}

export function resumeRecording(): void {
  if (!socket.connected) return;
  socket.emit("stream_resume", {});
}

export function sendAudioChunk(chunk: ArrayBuffer): void {
  if (!socket.connected) return;

  socket.emit("audio_chunk", chunk);
}

// ── Subscriptions ──────────────────────────────────────────────────

export function subscribeToTranscript(cb: TranscriptListener): () => void {
  transcriptListeners.push(cb);

  return () => {
    transcriptListeners = transcriptListeners.filter((l) => l !== cb);
  };
}

export function subscribeToCaptions(cb: CaptionListener): () => void {
  captionListeners.push(cb);

  return () => {
    captionListeners = captionListeners.filter((l) => l !== cb);
  };
}

export function subscribeToStatus(cb: StatusListener): () => void {
  statusListeners.push(cb);

  return () => {
    statusListeners = statusListeners.filter((l) => l !== cb);
  };
}
