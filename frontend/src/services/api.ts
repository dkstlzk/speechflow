/**
 * Real API layer wired to the Flask backend.
 * Endpoint contract is documented above each function.
 */
import type {
  ActionItem,
  ApiResponse,
  ProcessingStatus,
  Session,
  SummaryResponse,
  TranscriptResponse,
  TranscriptType,
} from "@/types";

const API_BASE =
  (import.meta.env.VITE_API_URL as string | undefined) ?? "http://localhost:5000";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

interface FetchOptions extends RequestInit {
  timeoutMs?: number;
}

async function apiFetch<T>(
  input: string,
  init: FetchOptions = {},
): Promise<ApiResponse<T>> {
  const { timeoutMs, ...rest } = init;
  const controller = new AbortController();
  const timer = timeoutMs
    ? setTimeout(() => controller.abort(), timeoutMs)
    : null;
  let res: Response;
  try {
    res = await fetch(input, { ...rest, signal: controller.signal });
  } finally {
    if (timer) clearTimeout(timer);
  }

  let json: { success?: boolean; data?: unknown; error?: string | null } = {};
  try {
    json = await res.json();
  } catch {
    // non-JSON response
  }

  if (!res.ok || json.success === false) {
    const msg =
      (json && json.error) ||
      `Request failed with status ${res.status}`;
    throw new ApiError(msg, res.status);
  }
  return { data: json.data as T, ok: true };
}

function mapBackendStatus(s: string): ProcessingStatus {
  const map: Record<string, ProcessingStatus> = {
    pending: "processing",
    uploaded: "processing",
    preprocessing: "processing",
    transcribing: "processing",
    diarizing: "processing",
    processing: "processing",
    completed: "completed",
    failed: "failed",
    // Realtime pipeline statuses
    recording: "recording",
    finalizing: "finalizing",
    review: "review",
    saved: "saved",
  };
  return map[s] ?? "processing";
}

// POST /api/upload/
export async function uploadFile(
  file: File,
): Promise<ApiResponse<{ sessionId: string }>> {
  const fd = new FormData();
  fd.append("file", file);
  const raw = await apiFetch<{
    session_id: number;
    status: string;
    filename: string;
  }>(`${API_BASE}/api/upload/`, { method: "POST", body: fd });
  return { data: { sessionId: String(raw.data.session_id) }, ok: true };
}

// GET /api/sessions/
export async function getSessions(): Promise<ApiResponse<Session[]>> {
  type BS = {
    id: number;
    status: string;
    session_type?: string;
    original_filename: string | null;
    created_at: string;
    transcript_type?: string | null;
    title?: string | null;
  };
  const raw = await apiFetch<BS[]>(`${API_BASE}/api/sessions/`);
  const sessions: Session[] = (raw.data ?? []).map((s) => ({
    id: String(s.id),
    createdAt: s.created_at,
    status: mapBackendStatus(s.status),
    transcriptType: (s.transcript_type as TranscriptType) ?? undefined,
    fileName: s.original_filename ?? undefined,
    title: s.title ?? undefined,
  }));
  return { data: sessions, ok: true };
}

// GET /api/sessions/{id}
export async function getSession(id: string): Promise<ApiResponse<Session>> {
  type BS = {
    id: number;
    status: string;
    transcript_type?: string | null;
    original_filename: string | null;
    created_at: string;
  };
  const raw = await apiFetch<BS>(`${API_BASE}/api/sessions/${id}`);
  return {
    data: {
      id: String(raw.data.id),
      createdAt: raw.data.created_at,
      status: mapBackendStatus(raw.data.status),
      transcriptType: raw.data.transcript_type as TranscriptType | undefined,
      fileName: raw.data.original_filename ?? undefined,
    },
    ok: true,
  };
}

// DELETE /api/sessions/{id}
export async function deleteSession(
  id: string,
): Promise<ApiResponse<{ sessionId: string }>> {
  const raw = await apiFetch<{ session_id: number }>(
    `${API_BASE}/api/sessions/${id}`,
    { method: "DELETE" },
  );
  return { data: { sessionId: String(raw.data.session_id) }, ok: true };
}

// GET /api/sessions/{id}/transcript
export async function getTranscript(
  id: string,
): Promise<ApiResponse<TranscriptResponse>> {
  type BC = {
    speaker: string;
    startSec: number;
    endSec: number;
    text: string;
    chunk_index: number;
  };
  type BP = { session_id: number | string; status: string; transcript: BC[] };
  const raw = await apiFetch<BP>(`${API_BASE}/api/sessions/${id}/transcript`);
  const segments = (raw.data.transcript ?? []).map((c) => ({
    speaker: c.speaker,
    text: c.text,
    chunk_index: c.chunk_index,
    startSec: c.startSec,
    endSec: c.endSec,
  }));
  return {
    data: {
      sessionId: String(raw.data.session_id),
      segments,
      rawText: segments.map((s) => `${s.speaker}: ${s.text}`).join("\n"),
    },
    ok: true,
  };
}

// GET /api/sessions/{id}/summary
export async function getSummary(
  id: string,
): Promise<ApiResponse<SummaryResponse>> {
  type BS = {
    session_id: number;
    summary: string;
    mom: string | null;
    created_at: string | null;
  };
  const raw = await apiFetch<BS>(`${API_BASE}/api/sessions/${id}/summary`);
  return {
    data: {
      sessionId: String(raw.data.session_id),
      summary: raw.data.summary,
      mom: raw.data.mom,
    },
    ok: true,
  };
}

// GET /api/actions/{session_id}
export async function getActions(
  id: string,
): Promise<ApiResponse<ActionItem[]>> {
  type BI = {
    id: number;
    text: string;
    status: string;
    created_at: string | null;
  };
  type BP = { session_id: number; action_items: BI[] };
  const raw = await apiFetch<BP>(`${API_BASE}/api/actions/${id}`);
  const items: ActionItem[] = (raw.data.action_items ?? []).map((it) => ({
    id: String(it.id),
    text: it.text,
    completed: it.status === "done",
  }));
  return { data: items, ok: true };
}

// POST /api/sessions/{id}/process
export async function processSession(
  id: string,
): Promise<ApiResponse<{ sessionId: string; status: "completed" }>> {
  const raw = await apiFetch<{
    session_id: number;
    transcript_type: string;
    summary: string;
  }>(`${API_BASE}/api/sessions/${id}/process`, {
    method: "POST",
    timeoutMs: 300000,
  });
  return {
    data: { sessionId: String(raw.data.session_id), status: "completed" },
    ok: true,
  };
}

export async function startRealtimeSession(): Promise<
  ApiResponse<{ sessionId: string }>
> {
  const raw = await apiFetch<{
    session_id: number;
    status: string;
  }>(`${API_BASE}/api/realtime/session`, {
    method: "POST",
  });

  return {
    data: {
      sessionId: String(raw.data.session_id),
    },
    ok: true,
  };
}

export async function finalizeRealtimeSession(
  id: string,
): Promise<ApiResponse<{ sessionId: string }>> {
  await apiFetch(
    `${API_BASE}/api/realtime/session/${id}/finalize`,
    {
      method: "POST",
    },
  );

  return {
    data: {
      sessionId: id,
    },
    ok: true,
  };
}

export async function saveRealtimeSession(
  id: string,
): Promise<ApiResponse<{ sessionId: string; title: string }>> {
  const raw = await apiFetch<{
    session_id: number;
    status: string;
    title: string;
  }>(`${API_BASE}/api/realtime/session/${id}/save`, {
    method: "POST",
  });

  return {
    data: {
      sessionId: String(raw.data.session_id),
      title: raw.data.title,
    },
    ok: true,
  };
}

export async function deleteRealtimeSession(
  id: string,
): Promise<ApiResponse<{ sessionId: string }>> {
  await apiFetch(
    `${API_BASE}/api/realtime/session/${id}`,
    {
      method: "DELETE",
    },
  );

  return {
    data: { sessionId: id },
    ok: true,
  };
}

export async function updateSessionTitle(
  id: string,
  title: string,
): Promise<ApiResponse<{ sessionId: string; title: string }>> {
  const raw = await apiFetch<{
    session_id: number;
    title: string;
  }>(`${API_BASE}/api/realtime/session/${id}/title`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });

  return {
    data: {
      sessionId: String(raw.data.session_id),
      title: raw.data.title,
    },
    ok: true,
  };
}
