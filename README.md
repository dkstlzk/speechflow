# SpeechFlow

SpeechFlow is a Flask-first speech-to-text and intelligent transcript processing platform.

It converts both uploaded audio/video files and real-time streaming audio into structured outputs including:

- Speaker-labeled transcripts (Diarization)
- Live transcript streaming
- Summaries
- Meeting Minutes (MoM)
- Action items

The project is designed around fully local, CPU-only inference using open-source models.

---

## Current MVP Status

### Completed

#### Upload Processing Pipeline
- MP3 and MP4 upload support
- FFmpeg audio extraction and normalization
- Background processing workflow

#### Realtime Reliability Features
- Session watchdog recovery
- Browser disconnect recovery
- Stale session cleanup
- Transcript ownership isolation
- Fast "live disposable captions" (0.3s) and persistent committed chunks
- Atomic row-level database locking (`SELECT FOR UPDATE`)

#### Realtime Streaming Infrastructure
- Bidirectional Socket.IO transport (Eventlet)
- In-browser microphone capture via WebRTC / `AudioContext`
- Chunk-based VAD (Voice Activity Detection) segmentation
- Live Faster-Whisper transcription with rolling acoustic context
- Delta-based transcript stabilization (Tentative vs Committed text)
- Resilient watchdog architecture for dropped connections
- Strict hardware privacy lifecycle (microphone teardown on pause)

#### Speaker Diarization (Offline)
- Two-Tier processing: "Quick" (clustering embeddings) and "Accurate" (full re-transcription + Pyannote)
- Isolated process execution (`multiprocessing.spawn`) to prevent memory leaks and segfaults
- Hysteresis-based alignment of Whisper transcript chunks to Pyannote speaker segments
- Orphan speaker cleanup and mapping

#### Intelligent Transcript Processing
- Transcript classification (e.g., Meeting, Lecture, Brainstorm)
- Summary and Meeting Minutes (MoM) generation
- Action item extraction (with parsed deliverables)
- Multilingual speech transcription (Hindi-English mixed speech, etc.)
- Full transcript and summary translation (Hindi, Tamil, Telugu, Marathi, etc.)
- Local LLM inference via Ollama (qwen2.5:3b)

#### Persistence & Management
- Unified session and transcript chunk storage with strict Unique Constraints
- Support for streaming real-time persistence
- Meeting Metadata Tracking (Title, Host, Participants)
- History tracking, session deletion, and cascading cleanup
- Indexed session discovery using PostgreSQL FTS (Full-Text Search)
- Detected language metadata and badging

#### Search & Retrieval
- PostgreSQL Full-Text Search (FTS)
- Transcript search highlighting
- Session discovery and filtering

#### Frontend UI
- Modern React + TypeScript interface ("Lovable" UI)
- Real-time live transcript timeline rendering
- Intelligent loading skeletons and declarative state management
- Realtime Audio Visualizer and connection status badge
- Transcript seek navigation
- Transcript export (.txt and .docx) with Translation and Metadata support
- Native Web Audio API tab/system capture combined with local microphone recording

#### Authentication & Access Control
- Session-based authentication using Flask secure cookies
- Login / Logout workflow
- Protected API routes
- Protected Socket.IO realtime connections
- Session persistence across browser refreshes
- Single-admin deployment model for MVP usage

---

## Architecture

```mermaid
flowchart TD

    subgraph Client
        A[Browser Microphone] --> B[Audio Context]
        B --> C[Socket.IO Client]
    end

    subgraph Backend
        C -->|Raw PCM Audio| D[Session Manager]
        D --> E[Realtime Worker]
    end

    subgraph Speech Pipeline
        E --> F[Silero VAD]
        F -->|Speech Segments| G[Faster Whisper]
    end

    subgraph Diarization Pipeline
        G -->|Offline Processing| M[Pyannote Audio]
        M --> N[Speaker Alignment]
        N --> H[(PostgreSQL)]
    end

    subgraph Persistence
        G -->|Transcript Chunks| H
    end

    subgraph Intelligence Layer
        H --> I[Ollama Classifier]
        I --> J[Summary and Action Items]
        J --> H
    end

    H --> K[React Frontend]
```

---

## Tech Stack

| Layer | Technology |
| :--- | :--- |
| **Realtime Transport** | Socket.IO (Flask-SocketIO + Eventlet) |
| **Backend Framework** | Flask, SQLAlchemy |
| **Frontend Framework** | React, TypeScript, Vite, Tailwind CSS |
| **Speech Recognition** | Faster-Whisper |
| **Voice Activity Detection** | Silero VAD |
| **Speaker Diarization** | Pyannote.audio (wespeaker-voxceleb) |
| **Database** | PostgreSQL |
| **Intelligence Generation** | Ollama (qwen2.5:3b) |
| **Audio Processing** | FFmpeg, pydub, AudioWorkletNode |

---

## Local Setup

### Prerequisites

- Python 3.10+
- PostgreSQL
- FFmpeg
- Ollama

### Required Environment Variables

Required:

```bash
SECRET_KEY=generate_a_secure_random_key_here
DATABASE_URL=postgresql://user:pass@localhost/speechflow
ADMIN_PASSWORD=your_admin_password
```

Required for diarization:

```bash
HF_TOKEN=your_huggingface_token
```

Optional:

```bash
OLLAMA_ENDPOINT=http://localhost:11434
OLLAMA_TIMEOUT_SECONDS=120
LOG_LEVEL=INFO
```

---

### Phase 1 — Upload Pipeline
✅ Complete

### Phase 2 — Intelligent Processing Layer
✅ Complete

### Phase 3 — Realtime Streaming Infrastructure
✅ Complete

### Phase 4 — Diarization, Reliability & Production Hardening
✅ Complete

### Phase 5 — Authentication & MVP Stabilization
✅ Complete

### Future Work
🚧 Multi-user support
🚧 User ownership and permissions
🚧 Deployment hardening
🚧 Eventlet migration
🚧 Storage quotas

---

## Current Limitations

- Authentication currently supports a single administrative user.
- Multi-user ownership and permissions are not implemented.
- **Deployment Architecture Constraint**: SpeechFlow currently assumes a single-process deployment (`gunicorn -w 1`) using Eventlet, without a Redis message queue backplane. Horizontal scaling requires migrating to a Redis-backed Socket.IO configuration.
- Eventlet remains the realtime transport layer and is a future migration candidate.
- **Production Recommendation**: Background jobs (Diarization, Intelligence, Translation) currently use local `multiprocessing`. If the backend crashes, jobs are lost. For production, replace local multiprocessing workers with **Celery + Redis task queues**.
- No application-level storage quotas are enforced.
- Delete requests during active diarization may still waste processing resources.
- Browser audio preprocessing (AGC, noise suppression, echo cancellation, microphone quality, room acoustics) can reduce speaker separability and lower realtime diarization accuracy compared to uploaded audio.

---

## Realtime Diarization Note

Realtime recordings and uploaded files do not necessarily produce identical diarization results.

Browser audio capture pipelines commonly apply:

- Automatic Gain Control (AGC)
- Noise Suppression
- Echo Cancellation

These transformations alter speaker characteristics before the audio reaches the diarization models.

As a result:

- Uploaded source audio may produce more accurate speaker separation.
- Realtime microphone recordings of the same content may produce fewer detected speakers.

This is an expected limitation of browser-based audio capture and not necessarily a defect in the diarization pipeline.

---

## License

MIT License