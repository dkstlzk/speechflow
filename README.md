# SpeechFlow

SpeechFlow is a Flask-first speech-to-text and intelligent transcript processing platform.

It converts both uploaded audio/video files and real-time streaming audio into structured outputs including:

- Speaker-labeled transcripts
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
- Delta stabilization
- Microphone privacy lifecycle

#### Realtime Streaming Infrastructure
- Bidirectional Socket.IO transport
- In-browser microphone capture via `AudioWorkletNode`
- Chunk-based VAD (Voice Activity Detection) segmentation
- Live Faster-Whisper transcription with rolling acoustic context
- Delta-based transcript stabilization (Tentative vs Committed text)
- Resilient watchdog architecture for dropped connections
- Strict hardware privacy lifecycle (microphone teardown on pause)

#### Intelligent Transcript Processing
- Transcript classification (e.g., Meeting, Lecture, Brainstorm)
- Summary and Meeting Minutes (MoM) generation
- Action item extraction
- Local LLM inference via Ollama (phi3:mini)

#### Persistence & Management
- Unified session and transcript chunk storage
- Support for streaming real-time persistence
- History tracking, session deletion, and cascading cleanup
- Indexed session discovery using PostgreSQL FTS

#### Frontend UI
- Modern React + TypeScript interface
- Real-time live transcript timeline rendering
- Intelligent loading skeletons and state management
- Session editing and dashboarding

---

## Architecture

```mermaid
flowchart TD

    subgraph Client
        A[Browser Mic] --> B[AudioWorklet]
        B --> C[Socket.IO Client]
    end

    subgraph Backend Transport
        C -->|Raw PCM| D[Session Manager]
        D --> E[Realtime Worker]
    end

    subgraph Speech Pipeline
        E --> F[Silero VAD]
        F -->|Segments| G[Faster-Whisper]
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
| **Realtime Transport** | Socket.IO (Flask-SocketIO) |
| **Backend Framework** | Flask, SQLAlchemy |
| **Frontend Framework** | React, TypeScript, Vite |
| **Speech Recognition** | Faster-Whisper |
| **Voice Activity Detection** | Silero VAD |
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

### Phase 4 — Session Management & Retrieval
🚧 Core session management complete; Advanced retrieval in progress

### Phase 5 — Frontend Integration
✅ Complete

### Phase 6 — Testing, Optimization & Deployment
🚧 In Progress (Demo Ready / Controlled User Testing)

---

## Current Limitations

- **Infrastructure**: Single backend instance; no horizontal scaling or Redis adapter.
- **State Management**: Realtime session manager operates entirely in-memory.
- **Performance**: CPU-only transcription introduces latency on older hardware.
- **Features**: Advanced semantic retrieval is not yet implemented. Speaker diarization is currently optimized for the batch upload pipeline only.
- **Intent**: Realtime transcription is currently optimized for MVP demonstrations and controlled user testing rather than massive concurrency.

---

## License

MIT License