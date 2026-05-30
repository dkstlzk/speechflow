# SpeechFlow Architecture

Date: 28/05/2026

## Objective

Document the finalized Phase 1 backend architecture for the upload transcription
pipeline in Flask.

## Phase 1 Status

PHASE 1 — Upload Transcription Pipeline is complete.

Implemented scope:

- Upload API (multipart audio)
- FFmpeg preprocessing (16kHz mono WAV)
- faster-whisper CPU transcription
- pyannote diarization
- Whisper to diarization alignment
- Speaker-labeled transcript persistence
- Ordered transcript retrieval API
- Threaded worker orchestration with lifecycle tracking

Out of scope for Phase 1:

- Realtime websocket streaming
- VAD-gated live transcription
- Summarization and action-item extraction

## Core Components

| Component | Responsibility |
| --- | --- |
| Flask | HTTP API for upload and transcript retrieval |
| SQLAlchemy | ORM and repository-backed persistence |
| PostgreSQL | Session, speaker, and transcript chunk storage |
| FFmpeg | Audio normalization pipeline |
| faster-whisper | CPU transcription engine |
| pyannote.audio | Speaker diarization |
| Background worker threads | Non-blocking upload pipeline execution |

## Modular Boundaries

- `api/`: upload and sessions endpoints
- `workers/`: threaded orchestration and stage transitions
- `services/audio/`: FFmpeg preprocessing wrappers
- `services/transcription/`: Whisper service and alignment logic
- `services/diarization/`: pyannote integration layer
- `services/persistence/`: session/speaker/chunk repositories
- `services/session/`: transcript retrieval assembly
- `models/`: SQLAlchemy entities (`Session`, `Speaker`, `TranscriptChunk`)
- `db/`: engine/session bootstrap
- `config/`: runtime settings and logging

## Finalized Upload Pipeline

`Upload -> FFmpeg -> Whisper -> Diarization -> Alignment -> Persistence -> Retrieval`

Stage lifecycle:

`pending -> preprocessing -> transcribing -> diarizing -> processing -> completed`

Failure lifecycle:

`<current_stage> -> failed`

## Transcript Contract

Final transcript chunks are persisted and reconstructed in chronological order
with this shape:

```json
{
  "speaker": "SPEAKER_00",
  "start": 0.0,
  "end": 1.7,
  "text": "example utterance",
  "order": 0
}
```

## Stability Notes

- Alignment uses conservative overlap thresholds and speaker-switch hysteresis to
  reduce unstable speaker flips on tiny overlaps.
- Transcript chunks are replaced per session on worker reruns to avoid
  persistence duplication.
- Retrieval enforces deterministic ordering by chunk index and timestamps.
- Worker cleanup removes temporary input and intermediate WAV files in both
  success and failure paths.
