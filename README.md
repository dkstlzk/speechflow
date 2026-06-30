# SpeechFlow

SpeechFlow is a local-first speech-to-text and transcript intelligence platform. It processes both real-time streaming audio and batch media uploads into structured, speaker-labeled transcripts with automated meeting intelligence and multilingual translation.

The system is designed around privacy-preserving, CPU-compatible local inference using open-weight models, ensuring audio data never leaves the host infrastructure.

## Core Capabilities

- **Streaming Transcription**: Low-latency, bidirectional Socket.IO audio streaming with rolling acoustic context and delta-based stabilization.
- **Batch Processing**: FFmpeg-powered media extraction pipeline for uploaded audio and video files.
- **Speaker Diarization**: Offline speaker clustering and alignment utilizing Pyannote Audio.
- **Meeting Intelligence**: Automated generation of summaries, meeting minutes, and action items using local LLMs.
- **Multilingual Translation**: Chunk-aware, context-preserving transcript translation for multiple regional languages.

## Architecture

```mermaid
flowchart TD
    subgraph Client [Frontend Interface]
        Browser[Browser Audio Context] --> Socket[Socket.IO Client]
        UI[React Application] --> HTTP[REST API]
    end

    subgraph Backend [Flask Application Server]
        Socket -->|Raw PCM| Realtime[Realtime Worker]
        HTTP --> Sessions[Session & Job Management]
    end

    subgraph Processing [Multiprocessing Workers]
        Realtime --> VAD[Silero VAD]
        VAD --> Whisper[Faster-Whisper]
        
        Sessions -->|Spawn| UploadWorker[Upload Pipeline]
        Sessions -->|Spawn| DiarizationWorker[Diarization Pipeline]
        Sessions -->|Spawn| IntelligenceWorker[Intelligence Pipeline]
        Sessions -->|Spawn| TranslationWorker[Translation Pipeline]
    end

    subgraph Inference [Local Models]
        Whisper
        DiarizationWorker --> Pyannote[Pyannote Audio]
        IntelligenceWorker --> OllamaSum[Ollama: Summarization]
        TranslationWorker --> OllamaTrans[Ollama: Translation]
    end

    subgraph Data [Persistence]
        Realtime --> Postgres[(PostgreSQL)]
        UploadWorker --> Postgres
        DiarizationWorker --> Postgres
        IntelligenceWorker --> Postgres
        TranslationWorker --> Postgres
    end
```

## Technical Stack

| Component | Technology |
| :--- | :--- |
| **Backend API** | Flask, SQLAlchemy, Eventlet |
| **Frontend UI** | React, TypeScript, Vite, Tailwind CSS |
| **Database** | PostgreSQL (with Full-Text Search) |
| **Speech Recognition** | Faster-Whisper |
| **Voice Activity Detection** | Silero VAD |
| **Speaker Diarization** | Pyannote Audio |
| **Language Models** | Ollama (Qwen 2.5 variants) |
| **Audio Processing** | FFmpeg, Pydub, AudioWorkletNode |
| **Concurrency** | Multiprocessing (Spawn Context), RLock Synchronization |

## Implementation Details

### Real-time Streaming
Audio capture relies on the native Web Audio API (`AudioContext`) with chunk-based transmission over WebSocket. The backend employs Silero VAD for voice activity detection, passing segmented audio to Faster-Whisper. The transcription output distinguishes between tentative (live) text and committed (finalized) chunks, maintaining low latency while preserving acoustic context.

### Background Processing
Heavy inference workloads (Diarization, Translation, Intelligence) are isolated into dedicated OS-level processes using `multiprocessing.spawn`. This guarantees memory isolation, prevents segmentation faults from C-bindings from affecting the main API server, and ensures blocking operations do not stall the asynchronous WebSocket event loop. A central `JobManager` tracks subprocess identifiers and handles graceful termination and state rollback.

### State and Persistence
Application state is centralized in PostgreSQL. Database transactions employ explicit `SELECT FOR UPDATE` row-level locks during concurrent transcription and diarization writes. Stale session recovery mechanisms automatically identify and reap orphaned background jobs based on configurable heartbeat thresholds.

## Environment Configuration

The application requires a `.env` configuration file in the project root. Refer to `.env.example` for the complete schema.

Required Variables:
```env
SECRET_KEY=cryptographically_secure_random_string
DATABASE_URL=postgresql://username:password@localhost/speechflow
ADMIN_PASSWORD=secure_admin_password
HF_TOKEN=huggingface_access_token_for_pyannote
```

Optional Overrides:
```env
OLLAMA_ENDPOINT=http://localhost:11434
OLLAMA_TIMEOUT_SECONDS=3600
MAX_BUFFER_MB=200
```

## Known Limitations

- **Authentication Constraints**: The current implementation restricts access to a single administrative user via Flask secure cookies. Multi-user role-based access control is not implemented.
- **Horizontal Scaling**: The architecture heavily utilizes single-process state management (`gunicorn -w 1` with Eventlet). Process-specific state dictionaries must be migrated to a distributed key-value store (e.g., Redis) before horizontal scaling is feasible.
- **Fault Tolerance**: Background task execution relies on local OS processes. In the event of a host failure, active background jobs cannot be automatically recovered. Production deployments should transition to dedicated task queues (e.g., Celery) for high availability.
- **Real-time Diarization Discrepancies**: Browser-based audio capture pipelines implicitly apply Automatic Gain Control (AGC), noise suppression, and echo cancellation. These transformations modify acoustic characteristics, which can reduce speaker separability and lower diarization accuracy compared to raw uploaded media.

## License

MIT License