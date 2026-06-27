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

const API_BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? "";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

interface FetchOptions extends RequestInit {
  timeoutMs?: number;
  credentials?: RequestCredentials;
}

async function apiFetch<T>(input: string, init: FetchOptions = {}): Promise<ApiResponse<T>> {
  const { timeoutMs, ...rest } = init;
  rest.credentials = rest.credentials || "include";
  const controller = new AbortController();
  const timer = timeoutMs ? setTimeout(() => controller.abort(), timeoutMs) : null;

  const abortHandler = () => controller.abort();
  if (init.signal) {
    init.signal.addEventListener("abort", abortHandler);
  }

  let res: Response;
  try {
    res = await fetch(input, { ...rest, signal: controller.signal });
  } catch (err) {
    throw err;
  } finally {
    if (timer) clearTimeout(timer);
    if (init.signal) {
      init.signal.removeEventListener("abort", abortHandler);
    }
  }

  let json: { success?: boolean; data?: unknown; error?: string | null } = {};
  try {
    json = await res.json();
  } catch (err) {
    // non-JSON response
  }

  if (!res.ok || json.success === false) {
    if (res.status === 401) {
      window.dispatchEvent(new Event("auth:unauthorized"));
    }
    const msg = (json && json.error) || `Request failed with status ${res.status}`;
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
    diarizing: "diarizing",
    processing: "processing",
    completed: "completed",
    failed: "failed",
    // Realtime pipeline statuses
    recording: "recording",
    finalizing: "finalizing",
    review: "processing", // Legacy alias
    saved: "completed", // Legacy alias
  };
  return map[s] ?? "processing";
}

// POST /api/upload/
export async function uploadFile(
  file: File,
  metadata?: { title?: string; host_name?: string; participants?: string }
): Promise<ApiResponse<{ sessionId: string }>> {
  const fd = new FormData();
  fd.append("file", file);
  if (metadata?.title) fd.append("title", metadata.title);
  if (metadata?.host_name) fd.append("host_name", metadata.host_name);
  if (metadata?.participants) fd.append("participants", metadata.participants);
  const raw = await apiFetch<{
    session_id: number;
    status: string;
    filename: string;
  }>(`${API_BASE}/api/upload/`, { method: "POST", body: fd });
  return { data: { sessionId: String(raw.data.session_id) }, ok: true };
}

// GET /api/sessions/
export async function getSessions(
  query?: string,
  signal?: AbortSignal,
): Promise<ApiResponse<Session[]>> {
  type BS = {
    id: number;
    status: string;
    session_type?: string;
    original_filename: string | null;
    created_at: string;
    transcript_type?: string | null;
    title?: string | null;
    has_audio?: boolean;
    audio_url?: string;
    duration_seconds?: number;
    detected_language?: string | null;
  };
  const url = query
    ? `${API_BASE}/api/sessions/?q=${encodeURIComponent(query)}`
    : `${API_BASE}/api/sessions/`;
  const raw = await apiFetch<BS[]>(url, { signal });
  const sessions: Session[] = (raw.data ?? []).map((s) => ({
    id: String(s.id),
    createdAt: s.created_at,
    status: mapBackendStatus(s.status),
    transcriptType: (s.transcript_type as TranscriptType) ?? undefined,
    fileName: s.original_filename ?? undefined,
    title: s.title ?? undefined,
    host_name: (s as any).host_name ?? undefined,
    participants: (s as any).participants ?? undefined,
    has_audio: s.has_audio,
    audio_url: s.audio_url ? `${API_BASE}${s.audio_url}` : undefined,
    durationSec: s.duration_seconds ?? undefined,
    diarized_at: (s as any).diarized_at ?? null,
    detected_language: s.detected_language ?? null,
    detected_languages: (s as any).detected_languages ?? null,
  }));
  return { data: sessions, ok: true };
}

// GET /api/sessions/{id}
export async function getSession(id: string, signal?: AbortSignal): Promise<ApiResponse<Session>> {
  type BS = {
    id: number;
    status: string;
    transcript_type?: string | null;
    original_filename: string | null;
    created_at: string;
    has_audio?: boolean;
    audio_url?: string;
    title?: string | null;
    duration_seconds?: number;
    detected_language?: string | null;
  };
  const raw = await apiFetch<BS>(`${API_BASE}/api/sessions/${id}`, { signal, cache: "no-store" });
  return {
    data: {
      id: String(raw.data.id),
      createdAt: raw.data.created_at,
      status: mapBackendStatus(raw.data.status),
      transcriptType: raw.data.transcript_type as TranscriptType | undefined,
      fileName: raw.data.original_filename ?? undefined,
      title: raw.data.title ?? undefined,
      host_name: (raw.data as any).host_name ?? undefined,
      participants: (raw.data as any).participants ?? undefined,
      has_audio: raw.data.has_audio,
      audio_url: raw.data.audio_url ? `${API_BASE}${raw.data.audio_url}` : undefined,
      durationSec: raw.data.duration_seconds ?? undefined,
      diarized_at: (raw.data as any).diarized_at ?? null,
      detected_language: raw.data.detected_language ?? null,
      detected_languages: (raw.data as any).detected_languages ?? null,
      processing_stage: (raw.data as any).processing_stage ?? undefined,
    },
    ok: true,
  };
}

// DELETE /api/sessions/{id}
export async function deleteSession(id: string): Promise<ApiResponse<{ sessionId: string }>> {
  const raw = await apiFetch<{ session_id: number }>(`${API_BASE}/api/sessions/${id}`, {
    method: "DELETE",
  });
  return { data: { sessionId: String(raw.data.session_id) }, ok: true };
}

// GET /api/sessions/{id}/transcript
export async function getTranscript(
  id: string,
  signal?: AbortSignal,
): Promise<ApiResponse<TranscriptResponse>> {
  type BC = {
    speaker: string;
    display_name?: string | null;
    startSec: number;
    endSec: number;
    text: string;
    chunk_index: number;
  };
  type BP = { session_id: number | string; status: string; transcript: BC[]; exists?: boolean };
  const raw = await apiFetch<BP>(`${API_BASE}/api/sessions/${id}/transcript`, { signal });
  if (raw.data && raw.data.exists === false) {
    throw new ApiError("Not found", 404);
  }
  const segments = (raw.data.transcript ?? []).map((c) => ({
    speaker: c.speaker,
    displayName: c.display_name ?? undefined,
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
  signal?: AbortSignal,
): Promise<ApiResponse<SummaryResponse>> {
  type BS = {
    session_id: number;
    summary: string;
    mom: string | null;
    history?: {
      iteration: number;
      summary: string;
      mom: string | null;
      created_at: string | null;
    }[];
    exists?: boolean;
  };
  const raw = await apiFetch<BS>(`${API_BASE}/api/sessions/${id}/summary`, { signal });
  if (raw.data && raw.data.exists === false) {
    throw new ApiError("Not found", 404);
  }
  return {
    data: {
      sessionId: String(raw.data.session_id),
      summary: raw.data.summary,
      mom: raw.data.mom,
      history: raw.data.history ?? [],
    },
    ok: true,
  };
}

// GET /api/actions/{session_id}
export async function getActions(
  id: string,
  signal?: AbortSignal,
): Promise<ApiResponse<ActionItem[]>> {
  type BI = {
    id: number;
    text: string;
    status: string;
    iteration?: number;
    created_at: string | null;
  };
  type BP = { session_id: number; action_items: BI[] };
  const raw = await apiFetch<BP>(`${API_BASE}/api/actions/${id}`, { signal });
  const items: ActionItem[] = (raw.data.action_items ?? []).map((it) => ({
    id: String(it.id),
    text: it.text,
    iteration: it.iteration ?? 1,
  }));
  return { data: items, ok: true };
}

// POST /api/sessions/{id}/process
export async function processSession(
  id: string,
): Promise<ApiResponse<{ sessionId: string; status: "completed" }>> {
  await apiFetch<{ message: string }>(`${API_BASE}/api/sessions/${id}/process`, {
    method: "POST",
    timeoutMs: 300000,
  });
  return {
    data: { sessionId: id, status: "completed" },
    ok: true,
  };
}

// POST /api/sessions/{id}/retry
export async function retrySession(
  id: string,
): Promise<ApiResponse<{ message: string }>> {
  const raw = await apiFetch<{ message: string }>(`${API_BASE}/api/sessions/${id}/retry`, {
    method: "POST",
  });
  return {
    data: raw.data,
    ok: true,
  };
}

// POST /api/sessions/{id}/quick-diarization
export async function processQuickDiarization(
  id: string,
): Promise<ApiResponse<{ message: string }>> {
  const raw = await apiFetch<{ message: string }>(`${API_BASE}/api/sessions/${id}/quick-diarization`, {
    method: "POST",
  });
  return {
    data: raw.data,
    ok: true,
  };
}

// POST /api/sessions/{id}/accurate-diarization
export async function processAccurateDiarization(
  id: string,
): Promise<ApiResponse<{ message: string }>> {
  const raw = await apiFetch<{ message: string }>(`${API_BASE}/api/sessions/${id}/accurate-diarization`, {
    method: "POST",
  });
  return {
    data: raw.data,
    ok: true,
  };
}

export async function startRealtimeSession(
  metadata?: { title?: string; host_name?: string; participants?: string }
): Promise<ApiResponse<{ sessionId: string }>> {
  const raw = await apiFetch<{
    session_id: number;
    status: string;
  }>(`${API_BASE}/api/realtime/session`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(metadata || {}),
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
  await apiFetch(`${API_BASE}/api/realtime/session/${id}/finalize`, {
    method: "POST",
  });

  return {
    data: {
      sessionId: id,
    },
    ok: true,
  };
}



export async function deleteRealtimeSession(
  id: string,
): Promise<ApiResponse<{ sessionId: string }>> {
  await apiFetch(`${API_BASE}/api/realtime/session/${id}`, {
    method: "DELETE",
  });

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
  }>(`${API_BASE}/api/sessions/${id}/title`, {
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

export async function updateSpeaker(
  id: string,
  speakerLabel: string,
  displayName: string,
): Promise<ApiResponse<{ sessionId: string; speakerLabel: string; displayName: string }>> {
  const raw = await apiFetch<{
    session_id: number;
    speaker_label: string;
    display_name: string;
  }>(`${API_BASE}/api/sessions/${id}/speakers/${encodeURIComponent(speakerLabel)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ display_name: displayName }),
  });

  return {
    data: {
      sessionId: String(raw.data.session_id),
      speakerLabel: raw.data.speaker_label,
      displayName: raw.data.display_name,
    },
    ok: true,
  };
}

// GET /api/sessions/languages
export async function getSupportedLanguages(): Promise<ApiResponse<Record<string, string>>> {
  const raw = await apiFetch<Record<string, string>>(`${API_BASE}/api/sessions/languages`);
  return { data: raw.data, ok: true };
}

// POST /api/sessions/{id}/translate
export interface TranslationResponse {
  id: number;
  session_id: number;
  target_language: string;
  translated_transcript: string | null;
  translated_summary: string | null;
  translated_mom: string | null;
  status: "translating" | "completed" | "failed" | "invalidated";
  error_message: string | null;
  created_at: string;
  updated_at: string;
  translated_chunks?: { chunk_id: number; text: string }[];
}

export async function translateSession(
  id: string,
  targetLanguage: string,
): Promise<ApiResponse<{ message: string }>> {
  const raw = await apiFetch<{ message: string }>(
    `${API_BASE}/api/sessions/${id}/translate`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ target_language: targetLanguage }),
    },
  );
  return { data: raw.data, ok: true };
}

export async function getTranslations(
  id: string,
  signal?: AbortSignal,
): Promise<ApiResponse<TranslationResponse[]>> {
  const raw = await apiFetch<TranslationResponse[]>(
    `${API_BASE}/api/sessions/${id}/translations`,
    { signal },
  );
  return { data: raw.data ?? [], ok: true };
}

