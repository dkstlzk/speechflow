# Worker Lifecycle

Date: 09/06/2026

## Objective

Describe the finalized threaded lifecycles used for Upload Processing, Real-Time Streaming, and Intelligence Generation in SpeechFlow.

## Worker Model

- `Upload Processing`: Runs via an isolated background process (`multiprocessing.get_context("spawn").Process`) kicked off on successful API file upload.
- `Real-Time Streaming`: Background daemon thread (`realtime_worker_loop`) continuously processes the active `StreamingSessionManager` buffer while a Socket.IO connection is alive.
- `Intelligence Generation`: Asynchronous execution via an isolated background process (`multiprocessing.get_context("spawn").Process`).

## Stage Transitions

### Upload Pipeline

Primary path:
`pending -> preprocessing -> transcribing -> diarizing -> processing -> completed`

Failure path:
`preprocessing|transcribing|diarizing|processing -> failed`

### Real-Time Pipeline

Primary path:
`recording -> finalizing -> processing -> completed`

Failure path:
`recording|finalizing|processing -> failed`

## Stage Responsibilities

1. `recording` (Real-Time Only)
- Client streams raw PCM bytes over WebSocket.
- Daemon loop runs Silero VAD.
- Chunked audio passed to Faster-Whisper.
- Intermediate results emitted over WebSocket.
- Finalized chunks committed to PostgreSQL.

2. `preprocessing` (Upload Only)
- Convert source media into normalized WAV using FFmpeg.

3. `transcribing` (Upload Only)
- Run faster-whisper and generate ordered transcript segments.

4. `diarizing` (Upload Only)
- Run pyannote and produce speaker intervals.

5. `finalizing` (Real-Time Only)
- Client issues `POST /api/realtime/{id}/finalize`.
- Flush remaining VAD buffer, generate final WAV artifact, mark DB.

6. `processing` (Both)
- Align transcript to diarization output (Upload Only).
- Persist speaker-labeled transcript chunks.
- Trigger `TranscriptProcessor` (Ollama LLM) to generate Classification, Summaries, MoM, and Action Items.

7. `completed`
- Mark lifecycle completion. Retrieval is fully available.

## Failure Handling

- Any unhandled exception marks the session `failed`.
- Error details are written to `processing_error`.
- **Isolated Database Recovery**: For real-time sessions, if the primary DB commit fails during teardown (or WAV generation crashes), an isolated `SessionLocal()` is spawned in the `except` block to forcibly write the `FAILED` status, preventing the frontend from getting stuck polling a dead `recording` state.
- **Intelligence Fallback**: If Ollama crashes or times out (`OllamaClientError`), it bubbles up gracefully, preventing silent DB corruption. Classification gracefully degrades to `"unknown"`.

## Cleanup Guarantees

Workers always attempt cleanup in `finally`:
- uploaded temp file
- preprocessed WAV artifact (for uploads)
- For crashed realtime sessions: raw corrupted `.raw` streams are safely renamed to `.orphan.[timestamp]` instead of being silently deleted.

## Determinism and Safety

- Warmups for Whisper and Pyannote models run in background threads on app startup to prevent the first request from timing out.
- Transcript persistence is replacement-based per session (for uploads) to prevent duplicate chunk accumulation on retries.
- **Server-Side Throttle (v1.0.0)**: Uses `get_active_job_count()` synchronized by `_jobs_lock` instead of unreliable `multiprocessing.active_children()` heuristics, fully preventing FFmpeg sub-processes from consuming Python worker slots.
- **WebSocket Concurrency (v1.0.0)**: Event handlers explicitly lock shared session state via `RLock` and safely retrieve sessions using the synchronized `get_session_by_sid()` accessor.
- Stale `recording` sessions (caused by abrupt server kills) are detected and auto-failed on boot via database-persisted `sample_rate` constraints.
