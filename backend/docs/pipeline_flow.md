# Pipeline Flow

Date: 09/06/2026

## Objective

Define the finalized execution flow and transcript reconstruction behavior for both Upload and Real-Time processing in SpeechFlow, including Intelligence Generation.

## 1. Batch Upload Flow

`Upload -> Temp File -> FFmpeg -> Whisper -> pyannote -> Alignment -> Persistence -> Intelligence -> Completed`

### Step-by-step

1. `POST /api/upload/` receives multipart audio and creates a session record (`pending`).
2. File is saved to `TEMP_DIR`.
3. Worker thread starts and marks session `preprocessing`.
4. FFmpeg normalizes audio to 16kHz mono WAV.
5. Worker marks `transcribing` and runs faster-whisper.
6. Worker marks `diarizing` and runs pyannote diarization.
7. Alignment service maps Whisper segments to speaker intervals.
8. Worker marks `processing`, resolves speaker IDs, and persists speaker-labeled chunks.
9. Intelligence processor triggers Ollama classification, summary, MoM, and action item generation.
10. Session transitions to `completed`.

## 2. Real-Time Streaming Flow

`Browser Mic -> Socket.IO -> Streaming Buffer -> VAD Chunking -> Whisper -> Transcript Persistence -> Stop Event -> Finalization -> Intelligence -> Completed`

### Step-by-step

1. `POST /api/realtime/start` initializes a new `realtime` session.
2. Frontend connects to Socket.IO and streams PCM audio chunks (`recording`).
3. `StreamingSessionManager` receives bytes and appends to an active buffer.
4. Daemon thread processes the buffer: Silero VAD looks for speech boundaries.
5. Detected chunks are passed to Faster-Whisper.
6. Tentative/partial chunks are emitted via WebSocket. Committed chunks are persisted to PostgreSQL `transcript_chunks`.
7. User clicks Stop: Frontend calls `POST /api/realtime/{id}/finalize`.
8. Audio processing finishes, buffer flushed to WAV artifact, session marked `processing`.
9. Intelligence processor triggers Ollama classification, summary, MoM, and action item generation.
10. Session transitions to `completed`.

## Intelligence Flow (Local LLM via Ollama)

- Requires completed transcript.
- Uses `qwen2.5:3b` via Ollama backend.
- `Classifier` assigns a type (e.g. `meeting`, `lecture`, `casual_conversation`).
- `SummaryGenerator` creates a paragraph summary.
- If type is `meeting` or similar, `MoMGenerator` creates detailed Meeting Minutes.
- `ActionItemExtractor` parses out specific assigned tasks.
- If Ollama is unavailable, explicit `503 Service Unavailable` with `OllamaClientError` is bubbled to the frontend.

## Alignment Behavior (Upload Only)

- Inputs are normalized and sorted deterministically.
- Speaker overlap is scored by total overlap per speaker label.
- Speaker switches require meaningful overlap strength.
- Tiny ambiguous overlaps use hysteresis to avoid rapid speaker jitter.
- Empty diarization output falls back to default speaker labeling.

## Persistence Behavior

- Transcript rows are persisted with fields: `session_id`, `speaker_id`, `start_time`, `end_time`, `text`, `chunk_index`, `is_partial`, `search_vector`.
- Upload flow uses session-level chunk replacement on reruns to avoid duplicate rows.
- Real-time flow uses append-only commits driven by VAD boundaries.

## Retrieval Flow

Endpoint: `GET /api/sessions/<id>` and `GET /api/sessions/<id>/transcript`

Ordering rule for reconstruction:
`chunk_index -> start_time -> end_time -> row_id`

## Failure and Cleanup

- Any stage exception updates the session to `failed` with `processing_error`.
- Real-time failures invoke an isolated DB transaction (`SessionLocal()`) to guarantee `FAILED` state transitions even if the primary transaction is poisoned.
- Worker always executes cleanup for original upload and generated WAV artifacts.
- Orphaned realtime `.raw` streams are safely archived to `.orphan.[timestamp]`.
