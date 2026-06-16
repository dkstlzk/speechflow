# SpeechFlow Architecture Reference (Current)

This document is the authoritative engineering architecture reference for SpeechFlow. It reflects the true implementation state of the codebase, explicitly delineating what exists today and what is deferred for future production scale.

---

## Section 1: Current System Overview

SpeechFlow is a full-stack, single-tenant ML application designed for recording, transcribing, diarizing, and extracting intelligence from audio sessions.

### Upload Pipeline
Files are uploaded via a synchronous HTTP endpoint (`/api/upload`). The upload is verified for basic extension allowance, persisted to a local `UPLOAD_DIR`, and then processed synchronously. Faster-Whisper transcribes the audio, generating `TranscriptChunk` rows. The session is marked `COMPLETED` immediately upon inference completion.

### Realtime Pipeline
The realtime pipeline uses WebSocket streaming (`flask-socketio`) combined with browser-based `AudioContext` and WebRTC `getUserMedia`.
1. **Frontend**: Samples microphone input natively and streams raw PCM packets over WebSockets.
2. **Backend Engine**: A background worker thread loops over a thread-safe `StreamingSessionManager`. 
3. **VAD Segmentation**: Raw audio is evaluated by a fast VAD model. Speech/silence boundaries dictate chunking.
4. **Processing**: Whisper transcribes chunks (executed synchronously to avoid `greenlet` thread-switching crashes associated with Eventlet).
5. **Channels**: The backend streams disposable `caption_update` events instantly and `transcript_committed` events for finalized chunks.

### Offline Diarization Pipeline
Diarization (speaker labeling) is entirely decoupled from the realtime ingestion pipeline to protect the main application process from heavy Pyannote inference crashes.
- **Quick Diarization**: Uses `AgglomerativeClustering` over generated embeddings.
- **Accurate Diarization**: Reruns the full Pyannote pipeline to generate highly accurate speaker timestamps, then aligns them to existing Whisper text chunks using temporal hysteresis.
- **Execution**: Both modes are isolated via `multiprocessing.spawn`. Row-level locks (`SELECT FOR UPDATE`) prevent concurrent execution.

### AI Summary & Action Item Generation
Triggered on demand. It reads the full transcript payload and prompts a local/remote LLM (via an `OllamaClient` interface) to generate a high-level summary, Minutes of Meeting (MoM), and actionable items (complete with owners and deadlines). These are saved persistently to PostgreSQL.

### Search
Powered by PostgreSQL Full Text Search (FTS). A GIN index on `tsvector` columns enables high-speed lexical search across all transcript text, session titles, and original filenames.

### Export System
Clients can export the transcript as a raw `.txt` file directly from the Realtime interface. An offline JSON/Markdown export structure is scaffolded but `.txt` is the primary, verified frontend export vehicle today.

### Session Lifecycle
1. `RECORDING`: Active microphone streaming.
2. `FINALIZING`: The user has pressed Stop; the backend is flushing the remaining buffer.
3. `COMPLETED`: The WAV file is securely written and transcription has successfully halted.
4. `DIARIZING` / `PROCESSING`: Background intelligence operations are running.
5. `FAILED`: The session crashed, or recovery logic caught a stale state on application startup.

---

## Section 2: Major Changes Since Phase 3

The following details the critical stabilization changes introduced to transition the MVP into a hardened, trusted-beta state.

### Realtime Pipeline Stabilization
- **SID Registration Ordering Fix**: The WebSocket `stream_start` event now synchronously registers the `StreamingSession` before acknowledging the frontend. This prevents a race where audio chunks arrived before the session existed.
- **Stream Start Sequencing**: The frontend now awaits backend confirmation before transmitting raw PCM chunks.
- **Finalize Lifecycle Hardening & TOCTOU Prevention**: A threading `Event` explicitly bridges the HTTP teardown request and the async background worker. To prevent TOCTOU race conditions where a fast-teardown marks a session as `FAILED`, endpoints now use row-level locking (`with_for_update()`) and respect the worker's natural teardown completion.
- **WAV Persistence Guarantees**: Background workers enforce `.wav` persistence before database commits.
- **CORS Audio Playback Compatibility**: `Content-Range`, `Accept-Ranges`, and `Content-Length` headers are explicitly exposed in the Flask CORS configuration to allow Chrome's `<audio>` player to calculate durations and perform range-requests on dynamically generated `.wav` files.
- **Failed Session Recovery**: Application startup now automatically sweeps any sessions left in `RECORDING`, `FINALIZING`, `DIARIZING`, or `PROCESSING` due to a server crash, marking them `FAILED`.

### Frontend Realtime State Machine
The frontend was refactored from imperative disjointed variables to a strict declarative state machine.
- **Connection States**: Explicit `connecting`, `connected`, `disconnected`, and `error` tracking.
- **Recording States**: `idle`, `recording`, `paused`, `finalizing`, `completed`.
- **Disconnect/Teardown Behavior**: If the socket drops (`disconnected`) while `recording`, a `useEffect` hook immediately stops the `AudioContext`, unbinds the microphone, sets the status to `completed`, and alerts the user via a 10-second toast. This eliminates the "phantom recording timer" bug.
- **Connection Badge Initial State Race**: A race condition where local instantaneous sockets fired `connected` before React subscriptions were mounted was resolved, ensuring the badge accurately reflects live network status.

### Offline Diarization Isolation
Diarization has been aggressively sandboxed to preserve system integrity.
- **Multiprocessing Spawn Worker Model**: Diarization invokes native `multiprocessing.get_context("spawn")`. This creates an entirely fresh Python interpreter. It prevents the notorious Pyannote memory leaks and segmentation faults from pulling down the main Flask application.
- **Database Safety Guarantees**: A new `SessionLocal` is initialized specifically inside the spawned worker to prevent cross-process connection pool corruption.

### Diarization Reliability Improvements
- **Row-level Locking**: Endpoints utilize SQLAlchemy's `with_for_update()` to serialize concurrent click-spam on Diarize buttons.
- **Active Recording Protection**: API endpoints explicitly block (`HTTP 400`) diarization if the target session is currently `RECORDING`, preventing data corruption.
- **Fields Reflected**: `diarization_mode` and `diarized_at` are properly exposed in the API serialization payload.

### Database Integrity Improvements
- **Transcript Chunk Uniqueness**: Added `UNIQUE (session_id, chunk_index)` constraint to `transcript_chunks`. Prevents duplicate chunk replication if the realtime pipeline issues a network retry.
- **Speaker Cleanup**: Overwriting/re-running accurate diarization now gracefully deletes orphaned `Speaker` rows, preventing ghost labels from re-attaching later.
- **Cascade Behavior**: Hard-deleting a session perfectly cascades downward via `ON DELETE CASCADE`, wiping chunks, action items, summaries, and speakers natively at the Postgres level.

### Search Improvements
- Native PostgreSQL FTS is fully leveraged with generated `tsvector` columns.
- Queries are efficiently routed using `to_tsquery`.

### Export Improvements
- `.txt` download via blob generation is fully active in the Realtime and Session views.

---

## Section 3: Known Limitations

> [!WARNING]
> The following are proven, documented limitations of the current architecture.

### Realtime Diarization Quality vs Offline Upload
**Realtime diarization quality will generally be worse than offline upload diarization.**

This is an expected artifact of browser-based audio capture, not a bug in the application logic. 
The browser's `navigator.mediaDevices.getUserMedia` API strictly enforces algorithms to optimize for human legibility over networks:
- Automatic Gain Control (AGC)
- Noise Suppression
- Echo Cancellation

These algorithms heavily compress dynamic range and strip the subtle acoustic and harmonic frequencies that the Pyannote clustering model relies on. 
**As a result:**
- An **Uploaded File** (uncompressed) might yield **5 speakers**.
- A **Realtime Recording** of the exact same meeting might yield **3 speakers**.
The model is mathematically forced to merge the highly homogenized voices.

### Authentication
**Authentication and authorization are not currently implemented.**
This has been intentionally deferred. Currently, any user with network access to the API can read, delete, or mutate any session. Do not deploy this branch to the public internet.

### Storage Quotas
There are no disk storage quotas. A user can upload unlimited audio files until the host disk is completely full.

### Eventlet Starvation Avoidance
The `flask-socketio` server uses `eventlet` for concurrency. Eventlet uses cooperative green-threads.
Faster-Whisper inference is a CPU-bound C++ process that blocks the Python GIL. 
- **Current Mitigation**: We previously wrapped `transcriber.transcribe` inside `eventlet.tpool.execute()`. However, this was reverted to synchronous execution due to severe `greenlet` thread-switching clashes and crashes. Currently, the ML inference blocks the Eventlet hub directly, resulting in minor event-loop stutters.
- **Deprecation Warning**: Eventlet is formally deprecated. A migration to `asyncio` (via FastAPI or Quart) is the strongly recommended path for Phase 2 to natively solve background processing without blocking transports.

---

## Section 4: Current Readiness Assessment

- **Internal MVP**: ✅ YES
- **Team Usage**: ✅ YES (Assuming a trusted environment)
- **Mentor Review**: ✅ YES
- **Demo Usage**: ✅ YES
- **Trusted Beta Usage**: ✅ YES
- **Public Production Usage**: ❌ NO (Blocked purely by the lack of Authentication, Authorization, and Rate Limiting).

**Reasoning**: The application does exactly what it is designed to do. State management is resilient, the database maintains perfect referential integrity, and audio streams no longer crash under load. It is a highly impressive technical achievement for an MVP timeline.

---

## Section 5: Architecture Decision Log

- **Why `multiprocessing.spawn` was chosen for offline diarization:** `fork` inherits parent memory structures and database connections, causing chaotic segfaults when combined with PyTorch/CUDA in a Flask context. `spawn` guarantees a pristine OS process.
- **Why row locking was introduced**: To solve classic TOCTOU (Time-of-Check to Time-of-Use) race conditions where concurrent button clicks duplicated ML processes, or where rapid Stop commands marked completing sessions as `FAILED`.
- **Why realtime finalization was hardened**: The HTTP requests were aggressively fighting the background thread over the database status. Introducing explicit row locking and delegating the final `COMPLETED` commit to the worker ensures perfect sync.
- **Why frontend teardown moved to declarative state management**: `useEffect` hooks explicitly watching connection states are vastly more resilient than imperative `if/else` callbacks scattered across Socket.io event listeners.
- **Why transcript uniqueness constraints were added:** As a safety net. The in-memory set handles 99% of deduplication, but if a crash occurs and the process recovers, Postgres now guarantees we never render the same chunk twice.
