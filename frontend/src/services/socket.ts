/**
 * Mock socket service. Replace internals with Socket.IO client later.
 * Components must only consume this abstraction.
 */
import { io, Socket } from "socket.io-client";
import type { StreamingEvent, TranscriptSegment } from "@/types";

const API_URL =
  import.meta.env.VITE_API_URL ||
  "http://localhost:5000";

export const socket: Socket = io(API_URL, {
  autoConnect: false,
  transports: ["websocket"],
});

type TranscriptListener = (chunk: TranscriptSegment) => void;
type StatusListener = (event: StreamingEvent) => void;

let transcriptListeners: TranscriptListener[] = [];
let statusListeners: StatusListener[] = [];

function emitStatus(
  type: string,
  message: string
) {
  const ev: StreamingEvent = {
    id: Math.random().toString(36).slice(2),
    timestamp: new Date().toISOString(),
    type,
    message,
  };
  statusListeners.forEach((l) => l(ev));
}

socket.on("connect", () => {
  emitStatus("connected", "Socket connected");
});

socket.on("disconnect", () => {
  emitStatus("disconnected", "Socket disconnected");
});

socket.on("connect_error", (err) => {
  emitStatus(
    "error",
    `Connection error: ${err.message}`
  );
});

socket.on("stream_ack", () => {
  emitStatus(
    "stream_started",
    "Backend acknowledged stream start"
  );
});

socket.on("stream_complete", () => {
  emitStatus(
    "stream_complete",
    "Backend finalized stream"
  );
});

socket.on("partial_transcript", (data) => {
  const segment: TranscriptSegment = {
    speaker:
      data.speaker || "Speaker",
    text:
      data.text ||
      data.status ||
      "",
  };

  transcriptListeners.forEach((l) =>
    l(segment)
  );
});

export async function connect(): Promise<void> {
  emitStatus(
    "connecting",
    "Establishing connection..."
  );

  if (socket.connected) {
    return;
  }

  await new Promise<void>(
    (resolve, reject) => {
      const timeout = setTimeout(() => {
        socket.off("connect");
        socket.off("connect_error");

        reject(
          new Error(
            "Socket connection timeout"
          )
        );
      }, 5000);

      socket.once("connect", () => {
        clearTimeout(timeout);
        resolve();
      });

      socket.once(
        "connect_error",
        (err) => {
          clearTimeout(timeout);
          reject(err);
        }
      );

      socket.connect();
    }
  );
}

export function disconnect(): void {
  if (socket.connected) {
    socket.disconnect();
  }
}

export function isConnected(): boolean {
  return socket.connected;
}

export function startRecording(
  sessionId: string
): void {
  if (!socket.connected) return;

  emitStatus(
    "session_started",
    `Session ${sessionId} started`
  );

  socket.emit("stream_start", {
    session_id: sessionId,
  });
}

export function stopRecording(): void {
  if (!socket.connected) return;

  socket.emit("stream_end", {});

  emitStatus(
    "session_finalized",
    "Session finalized"
  );
}

export function sendAudioChunk(
  chunk: ArrayBuffer
): void {
  if (!socket.connected) return;

  socket.emit("audio_chunk", chunk);
}

export function subscribeToTranscript(
  cb: TranscriptListener
): () => void {
  transcriptListeners.push(cb);

  return () => {
    transcriptListeners =
      transcriptListeners.filter(
        (l) => l !== cb
      );
  };
}

export function subscribeToStatus(
  cb: StatusListener
): () => void {
  statusListeners.push(cb);

  return () => {
    statusListeners =
      statusListeners.filter(
        (l) => l !== cb
      );
  };
}