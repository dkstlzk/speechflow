/**
 * Mock API layer. Swap implementations with real Flask endpoints later.
 * Endpoint contract is documented above each function.
 */
import type {
  ActionItem,
  ApiResponse,
  Session,
  SummaryResponse,
  TranscriptResponse,
} from "@/types";

const delay = (ms: number) => new Promise((r) => setTimeout(r, ms));

const MOCK_SESSIONS: Session[] = [
  {
    id: "sess_001",
    createdAt: "2026-05-28T10:12:00Z",
    status: "completed",
    transcriptType: "meeting",
    fileName: "weekly-sync.mp3",
    durationSec: 1820,
  },
  {
    id: "sess_002",
    createdAt: "2026-05-29T14:45:00Z",
    status: "completed",
    transcriptType: "interview",
    fileName: "candidate-interview.mp4",
    durationSec: 2640,
  },
  {
    id: "sess_003",
    createdAt: "2026-05-30T09:00:00Z",
    status: "processing",
    transcriptType: "lecture",
    fileName: "lecture-04.wav",
    durationSec: 3300,
  },
];

const ok = <T>(data: T): ApiResponse<T> => ({ data, ok: true });

// POST /api/upload
export async function uploadFile(
  file: File,
): Promise<ApiResponse<{ sessionId: string }>> {
  await delay(900);
  const sessionId = `sess_${Math.random().toString(36).slice(2, 8)}`;
  MOCK_SESSIONS.unshift({
    id: sessionId,
    createdAt: new Date().toISOString(),
    status: "processing",
    transcriptType: "meeting",
    fileName: file.name,
  });
  return ok({ sessionId });
}

// GET /api/sessions
export async function getSessions(): Promise<ApiResponse<Session[]>> {
  await delay(300);
  return ok(MOCK_SESSIONS);
}

// GET /api/sessions/{id}
export async function getSession(id: string): Promise<ApiResponse<Session>> {
  await delay(200);
  const s =
    MOCK_SESSIONS.find((x) => x.id === id) ?? {
      id,
      createdAt: new Date().toISOString(),
      status: "completed" as const,
      transcriptType: "meeting" as const,
    };
  return ok(s);
}

// GET /api/sessions/{id}/transcript
export async function getTranscript(
  id: string,
): Promise<ApiResponse<TranscriptResponse>> {
  await delay(400);
  const segments = [
    { speaker: "Participant A", text: "Hello everyone, thanks for joining the call today.", startSec: 0 },
    { speaker: "Participant B", text: "Happy to be here. Should we start with the roadmap?", startSec: 6 },
    { speaker: "Participant A", text: "Yes, let's begin by reviewing Q3 deliverables.", startSec: 12 },
    { speaker: "Participant C", text: "I have a few concerns about the timeline I'd like to discuss.", startSec: 20 },
    { speaker: "Participant B", text: "Sure, let's open that up after the roadmap section.", startSec: 28 },
  ];
  return ok({
    sessionId: id,
    segments,
    rawText: segments.map((s) => `${s.speaker}: ${s.text}`).join("\n"),
  });
}

// GET /api/sessions/{id}/summary
export async function getSummary(
  id: string,
): Promise<ApiResponse<SummaryResponse>> {
  await delay(400);
  return ok({
    sessionId: id,
    summary:
      "The team reviewed Q3 deliverables, discussed concerns around the timeline, and aligned on next steps for the roadmap.",
    mom: [
      "Attendees: Participant A, B, C",
      "Agenda: Q3 roadmap review",
      "Decisions: Adjust timeline for module 2",
      "Next meeting: Following week",
    ].join("\n"),
  });
}

// GET /api/actions/{session_id}
export async function getActions(
  id: string,
): Promise<ApiResponse<ActionItem[]>> {
  await delay(300);
  return ok([
    { id: "a1", text: "Share updated roadmap doc", owner: "Participant A", dueDate: "2026-06-05" },
    { id: "a2", text: "Schedule follow-up with engineering", owner: "Participant B" },
    { id: "a3", text: "Draft revised timeline proposal", owner: "Participant C", dueDate: "2026-06-07" },
  ]);
}

// POST /api/sessions/{id}/process
export async function processSession(
  id: string,
): Promise<ApiResponse<{ sessionId: string; status: "processing" }>> {
  await delay(600);
  return ok({ sessionId: id, status: "processing" });
}

// POST /api/realtime/sessions  (placeholder)
export async function startRealtimeSession(): Promise<
  ApiResponse<{ sessionId: string }>
> {
  await delay(300);
  return ok({ sessionId: `rt_${Math.random().toString(36).slice(2, 8)}` });
}

// POST /api/realtime/sessions/{id}/finalize  (placeholder)
export async function finalizeRealtimeSession(
  id: string,
): Promise<ApiResponse<{ sessionId: string }>> {
  await delay(400);
  return ok({ sessionId: id });
}
