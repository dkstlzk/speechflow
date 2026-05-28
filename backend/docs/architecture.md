# SpeechFlow Architecture

Date: 28/05/2026

## Objective

Define the Flask-native, CPU-only architecture for SpeechFlow and describe the
core components, execution model, and system boundaries that guide Phase 1
implementation.

## MVP Scope

- Upload transcription for MP3/MP4/WAV
- Realtime streaming with live captions
- Speaker diarization and alignment
- Transcript persistence and session history
- Summary, MOM, and action item extraction
- TXT/JSON export

## Core Components

| Component | Responsibility |
| --- | --- |
| Flask | HTTP API layer (upload, sessions, actions) |
| Flask-SocketIO | Realtime streaming and caption events |
| SQLAlchemy | ORM and persistence mapping |
| PostgreSQL | Session and transcript storage |
| FFmpeg | Audio normalization (16kHz mono WAV) |
| faster-whisper | Speech-to-text inference |
| Silero VAD | Speech activity gating for streaming |
| pyannote.audio | Speaker diarization |
| Ollama | Summary, MOM, and action extraction |

## Execution Model

- Flask handles API calls synchronously.
- Flask-SocketIO runs in threading mode for realtime events.
- Long-running work uses background threads, not async frameworks.
- No Celery/Redis for MVP unless blocking becomes unmanageable.

## Service Boundaries (Repo Mapping)

- api/: Flask Blueprints for upload, sessions, and actions.
- websocket/: SocketIO event handlers and streaming contract.
- services/audio/: FFmpeg preprocessing helpers.
- services/transcription/: Whisper inference and rolling buffer.
- services/diarization/: pyannote segmentation.
- services/summarization/: Ollama interaction and prompts.
- services/persistence/: database writes and reads.
- services/session/: session lifecycle helpers.
- services/utils/: temp file management utilities.
- workers/: background thread helpers.
- models/: SQLAlchemy models.
- schemas/: response payload shapes.
- db/: SQLAlchemy base and session.
- config/: settings, constants, and logging setup.

## Data Flow Overview

Upload pipeline:

Upload -> FFmpeg -> Whisper -> Diarization -> Alignment -> DB -> Summary

Streaming pipeline:

MediaRecorder -> SocketIO -> Rolling Buffer + VAD -> Whisper -> DB
-> Diarization -> Summary

## Session Status Lifecycle

pending -> uploaded -> preprocessing -> transcribing -> diarizing
-> processing -> completed

Failure path:

pending -> failed

## Model Selection and Fallbacks

- faster-whisper uses small or base models with int8 for CPU-friendly speed.
- pyannote requires a HuggingFace token and runs locally.
- Ollama uses phi3:mini as primary with llama3.2 or bart-large-cnn fallback.

## Known Risks and Mitigations

- CPU latency may exceed realtime targets on long sessions.
  - Mitigation: smaller Whisper models, int8, VAD gating, shorter windows.
- Diarization quality drops on noisy audio.
  - Mitigation: enforce preprocessing and encourage clean inputs.
- Long transcripts exceed local LLM context.
  - Mitigation: chunk summaries and combine outputs.
- Streaming chunk order can drift.
  - Mitigation: enforce chunk_index ordering and timestamps.
