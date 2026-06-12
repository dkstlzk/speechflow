# SpeechFlow Architecture

Date: 09/06/2026

## Objective

Document the finalized backend architecture for SpeechFlow, encompassing the upload transcription pipeline, real-time streaming pipeline, and intelligence layer.

## Project Status

**Phase 1 — Upload Transcription Pipeline:** Complete
**Phase 2 — Intelligence Layer:** Complete
**Phase 3 — Real-Time Streaming Infrastructure:** Complete
**Phase 4 — Session Management & Retrieval:** Complete
**Phase 5 — Frontend Integration:** Complete

Implemented scope:
- Upload API (multipart audio)
- Realtime WebSocket API (Socket.IO with AudioWorkletNode)
- FFmpeg preprocessing (16kHz mono WAV)
- VAD (Voice Activity Detection) segmentation via Silero
- faster-whisper CPU transcription (live & batch)
- pyannote diarization (batch upload only)
- Whisper to diarization alignment
- Speaker-labeled transcript persistence
- Intelligence Generation (Classification, Summaries, MoM, Action Items) via Ollama
- Deterministic transcript chunk and intelligence retrieval APIs
- Full fault-tolerance with isolated database recovery transactions

## Core Components

| Component | Responsibility |
| --- | --- |
| Flask | HTTP API for upload, sessions, and retrieval |
| Socket.IO | Bidirectional WebSocket transport for real-time PCM audio streaming |
| SQLAlchemy | ORM and repository-backed persistence |
| PostgreSQL | Session, speaker, chunk, summary, and action item storage with FTS indexing |
| FFmpeg | Audio normalization pipeline |
| Silero VAD | Realtime audio chunk segmentation |
| faster-whisper | CPU transcription engine |
| pyannote.audio | Speaker diarization |
| Ollama | Local LLM inference engine for intelligent extraction |
| Background worker threads | Non-blocking execution for realtime streaming, upload processing, and intelligence generation |

## Modular Boundaries

- `api/`: Upload, sessions, realtime endpoints
- `workers/`: Threaded orchestration for `upload_pipeline.py` and `realtime/worker.py`
- `websocket.py`: Socket.IO event registrations and lifecycle mapping
- `services/audio/`: FFmpeg preprocessing wrappers
- `services/transcription/`: Whisper service, alignment logic, VAD, and `streaming.py` session management
- `services/diarization/`: pyannote integration layer
- `services/summarization/`: Ollama client, prompt templates, and `TranscriptProcessor`
- `services/persistence/`: Dedicated repositories for sessions, speakers, transcripts, summaries, and action items
- `services/session/`: Aggregated retrieval assembly
- `models/`: SQLAlchemy entities (`Session`, `Speaker`, `TranscriptChunk`, `Summary`, `ActionItem`)
- `db/`: Engine, session bootstrap, and Alembic migrations
- `config/`: Runtime settings and logging

## Finalized Execution Flows

### 1. Upload Pipeline
`Upload -> FFmpeg -> Whisper -> Diarization -> Alignment -> Persistence -> Intelligence Generation -> Completed`

### 2. Real-Time Pipeline
`Socket.IO -> Streaming Buffer -> VAD Chunking -> Whisper -> Transcript Persistence -> Finalization -> Intelligence Generation -> Completed`

## Session Lifecycle

Upload status flow:
`pending -> preprocessing -> transcribing -> diarizing -> processing -> completed`

Real-time status flow:
`recording -> finalizing -> processing -> completed`

Failure lifecycle:
`<current_stage> -> failed`

## Transcript Contract

Final transcript chunks are persisted in chronological order with this shape:

```json
{
  "speaker": "SPEAKER_00",
  "start": 0.0,
  "end": 1.7,
  "text": "example utterance",
  "order": 0
}
```

## Stability & Fault-Tolerance Notes

- Real-time pipeline features isolated database recovery transactions. If background WAV conversion fails, the session safely updates to `failed` to prevent frontend polling hangs.
- Stale, orphaned `recording` sessions are automatically reset to `failed` upon backend startup.
- Whisper and Pyannote models run warmup tasks via daemon threads on boot.
- Intelligence requests failing via Ollama explicitly trigger `503 Service Unavailable` with `OllamaClientError`.
- Retrieval enforces deterministic ordering by chunk index and timestamps.
- Worker cleanup reliably removes temporary input and intermediate WAV files in both success and failure paths.
