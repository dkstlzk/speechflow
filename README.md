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
- Local LLM inference via Ollama (phi3:mini)

#### Persistence & Management
- Unified session and transcript chunk storage with strict Unique Constraints
- Support for streaming real-time persistence
- History tracking, session deletion, and cascading cleanup
- Indexed session discovery using PostgreSQL FTS (Full-Text Search)

#### Frontend UI
- Modern React + TypeScript interface ("Lovable" UI)
- Real-time live transcript timeline rendering
- Intelligent loading skeletons and declarative state management
- Realtime Audio Visualizer and connection status badge
- Transcript seek navigation and `.txt` export

---

## Architecture

```mermaid
flowchart TD

    subgraph Client
        A[Browser Mic] --> B[AudioContext]
        B --> C[Socket.IO Client]
    end

    subgraph Backend Transport
        C -->|Raw PCM| D[Session Manager]
        D --> E[Realtime Worker (Eventlet Synchronous)]
    end

    subgraph Speech Pipeline
        E --> F[Silero VAD]
        F -->|Segments| G[Faster-Whisper]
    end
    
    subgraph Diarization Pipeline
        G -->|Offline Post-Processing| M[Pyannote.audio]
        M --> N[Speaker Alignment]
        N --> H
    end

    subgraph Database
        G -->|Transcript Chunks| H[(PostgreSQL)]
    end

    subgraph Intelligence Layer
        H --> I[Ollama Classifier]
        I --> J[Summary & Action Items]
        J --> H
    end

    H --> K[Frontend UI]
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
| **Intelligence Generation** | Ollama (phi3:mini) |
| **Audio Processing** | FFmpeg, pydub, AudioWorkletNode |

---

## Local Setup

### Prerequisites

- Python 3.10+
- PostgreSQL
- FFmpeg
- Ollama

### Environment Variables

```bash
DATABASE_URL=postgresql://user:pass@localhost/speechflow
OLLAMA_ENDPOINT=http://localhost:11434
OLLAMA_TIMEOUT_SECONDS=120
HF_TOKEN=your_huggingface_token
SECRET_KEY=generate_a_secure_random_key_here
```

### Backend & Frontend

```bash
# Backend
pip install -r backend/requirements/base.txt
python -m backend.app.main

# Frontend
cd frontend
npm install
npm run dev
```

---

## Roadmap

### Phase 1 — Upload Pipeline
✅ Complete

### Phase 2 — Intelligent Processing Layer
✅ Complete

### Phase 3 — Streaming Infrastructure
✅ Complete

### Phase 4 — Diarization, Hardening & Retrieval
✅ Complete

### Phase 5 — Frontend Integration
✅ Complete

### Phase 6 — Deployment & Multi-Tenant Support
🚧 Pending

---

## Current Limitations

- **Authentication/Authorization**: There is currently no authentication layer. Any client with network access can read or delete any session. The backend should not be exposed to the public internet.
- **Diarization Quality vs Realtime Compression**: Realtime WebRTC audio capture applies aggressive Auto Gain Control (AGC) and Noise Suppression. This destroys acoustic embeddings, forcing Pyannote to artificially merge speakers (e.g. 5 real speakers may be clustered as 3). This is an expected hardware/browser limitation, not a pipeline bug.
- **Eventlet Deprecation**: The backend uses `eventlet` for WebSocket concurrency. Due to `greenlet` thread-clash crashes, heavy ML tasks currently block the Eventlet hub synchronously. A future migration to `asyncio` is recommended to natively handle asynchronous background processing.
- **Storage Quotas**: There are no application-level storage quotas.

---

## License

MIT License