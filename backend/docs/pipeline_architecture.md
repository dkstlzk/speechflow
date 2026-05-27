# SpeechFlow Pipeline Architecture

Date: 27/05/2026

## Objective

Define the complete processing architecture for:
- upload-based transcription
- realtime streaming transcription
- speaker diarization
- transcript persistence
- intelligent transcript processing

This document finalizes the high-level backend execution flow before implementation begins.

---

# Core System Overview

SpeechFlow consists of two primary processing pipelines:

1. Upload Processing Pipeline
2. Realtime Streaming Pipeline

Both pipelines eventually converge into:
- transcript persistence
- speaker diarization
- summarization
- action extraction
- session retrieval APIs

---

# High-Level Architecture

```text
Audio Input
    ↓
Preprocessing
    ↓
Whisper Transcription
    ↓
Speaker Diarization
    ↓
Transcript Alignment
    ↓
Persistence Layer
    ↓
Transcript Intelligence
    ↓
Frontend/API Retrieval
```

---

# Core Backend Components

| Component | Responsibility |
|---|---|
| FastAPI | API + WebSocket server |
| FFmpeg | audio preprocessing |
| faster-whisper | speech-to-text inference |
| pyannote.audio | speaker diarization |
| Silero VAD | speech activity detection |
| PostgreSQL | persistence layer |
| Ollama + phi3 | summarization + extraction |

---

# 1. Upload Processing Pipeline

Used for:
- MP3 uploads
- WAV uploads
- MP4 uploads
- recorded meeting uploads

---

# Upload Pipeline Flow

```text
Upload
→ temp file save
→ FFmpeg preprocessing
→ 16kHz mono WAV normalization
→ faster-whisper transcription
→ pyannote speaker segmentation
→ transcript-speaker alignment
→ transcript chunk persistence
→ summary generation
→ action item extraction
→ final session persistence
→ API response
```

---

# Step-by-Step Explanation

---

## Upload Endpoint

Frontend uploads:
- MP3
- WAV
- MP4

via FastAPI upload endpoint.

Example future endpoint:

```text
POST /upload
```

---

## Temporary File Storage

Uploaded files stored temporarily inside:

```text
temp/
```

Reason:
- FFmpeg processing requires local file access
- Whisper inference prefers normalized files

Temporary files should be deleted after:
- successful processing
- processing failure
- abandoned sessions

to prevent long-term disk accumulation.

---

## FFmpeg Preprocessing

All audio normalized into:

```text
16kHz mono WAV
```

Reason:
- consistent inference behavior
- optimized Whisper compatibility
- simpler downstream processing

---

## Whisper Transcription

faster-whisper generates:
- transcript text
- timestamps
- transcript segments

Output example:

```json
{
  "start": 12.3,
  "end": 14.8,
  "text": "Today we finalized the backend architecture."
}
```

---

## pyannote Speaker Segmentation

pyannote generates:
- speaker regions
- speaker segmentation timestamps

Example:

```json
{
  "speaker": "SPEAKER_00",
  "start": 12.0,
  "end": 15.0
}
```

---

## Transcript-Speaker Alignment

Alignment step combines:
- Whisper transcript timestamps
- speaker diarization regions

Goal:

```text
Whisper text
↔
speaker label
```

Final output:

```json
{
  "speaker": "SPEAKER_00",
  "start": 12.3,
  "end": 14.8,
  "text": "Today we finalized the backend architecture."
}
```

---

## Transcript Persistence

Persist:
- transcript chunks
- speaker mappings
- session metadata

into PostgreSQL.

---

## Transcript Intelligence

Send finalized transcript to:
- Ollama
- phi3:mini

Generate:
- summary
- MOM
- action items
- key discussion points

---

## Final API Response

Frontend receives:
- transcript
- speakers
- summary
- MOM
- action items

---

# 2. Realtime Streaming Pipeline

Used for:
- live microphone transcription
- realtime caption generation
- streaming sessions

---

# Streaming Pipeline Flow

```text
Browser microphone
→ MediaRecorder WebM/Opus chunks
→ WebSocket streaming
→ backend ring buffer
→ FFmpeg conversion
→ Silero VAD gating
→ rolling Whisper inference
→ incremental caption updates
→ transcript persistence
→ session finalization
→ post-session diarization
→ summary generation
```

---

# Step-by-Step Explanation

---

## Browser Audio Capture

Frontend captures microphone audio using:

```text
MediaRecorder API
```

Browser generates:
- WebM/Opus chunks

Reason:
- browser-native support
- efficient chunk transport
- lightweight streaming

---

## WebSocket Streaming

Audio chunks streamed continuously via:

```text
WebSocket
```

Reason:
- realtime bidirectional communication
- low latency streaming
- incremental updates

---

## Backend Ring Buffer

Incoming audio stored temporarily in rolling memory buffer.

Purpose:
- accumulate short inference windows
- support rolling transcription

Typical window:

```text
3–5 seconds
```

---

## FFmpeg Conversion

WebM/Opus chunks converted internally into:
- WAV
- PCM audio

before Whisper inference.

---

## Silero VAD

Voice Activity Detection filters:
- silence
- noise-only segments

Reason:
- reduce unnecessary Whisper inference
- improve CPU efficiency

---

## Rolling Whisper Inference

Instead of processing entire sessions:
- repeatedly transcribe small rolling windows

Example:
- every 4–5 seconds

Result:
- realtime caption generation

---

## Incremental Caption Updates

Partial transcripts pushed back to frontend continuously.

Example:

```json
{
  "partial": true,
  "text": "Today we finalized"
}
```

---

## Transcript Persistence

Streaming transcript chunks persisted incrementally into PostgreSQL.

Important:
- ordering uses timestamps/chunk_index
- insertion order cannot be trusted

---

## Post-Session Diarization

Realtime diarization is intentionally NOT performed during active streaming.

Reason:
- CPU constraints
- memory pressure
- latency concerns

Instead:
- diarization runs after session completion

This architecture was validated during local benchmarking.

---

## Post-Processing

After session ends:
- transcript finalized
- diarization completed
- summary generated
- action items extracted

---

# 3. Persistence Architecture

Both upload and streaming pipelines eventually converge into:

```text
sessions
transcript_chunks
speakers
session_summary
action_items
```

This unified persistence model simplifies:
- retrieval APIs
- frontend rendering
- exports
- session history

---

# 4. Service Layer Responsibilities

---

## ffmpeg_service.py

Handles:
- format conversion
- WAV normalization
- preprocessing

---

## whisper_service.py

Handles:
- transcription
- segment generation
- inference management

---

## diarization_service.py

Handles:
- speaker segmentation
- speaker region generation

---

## transcript_service.py

Handles:
- transcript reconstruction
- chunk ordering
- alignment logic
- transcript merging

---

## ollama_service.py

Handles:
- summary generation
- MOM extraction
- action item extraction

---

# 5. Important Architecture Decisions

---

## WAV as Internal Standard

All audio normalized internally into:

```text
16kHz mono WAV
```

Reason:
- consistent inference behavior
- simpler processing pipeline
- stable Whisper compatibility

---

## Chunk-Based Persistence

Transcript persistence uses incremental chunks rather than giant transcript blobs.

Reason:
- realtime streaming support
- partial updates
- scalable persistence
- timestamp reconstruction

---

## Post-Session Diarization

Realtime diarization intentionally avoided.

Reason:
- CPU-only deployment constraints
- pyannote latency concerns
- memory pressure observed during benchmarking

---

## Async Backend Architecture

FastAPI async endpoints selected because:
- uploads are long-running
- inference is expensive
- WebSockets require non-blocking handling
- multiple sessions may run concurrently

---

# 6. Known Risks

| Risk | Description |
|---|---|
| pyannote latency | long recordings may become slow |
| CPU memory pressure | Whisper + Ollama coexistence heavy |
| transcript ordering | async chunk ordering complexity |
| streaming synchronization | rolling inference overlap handling |
| long transcript summarization | chunking strategy may be required |
| temp storage growth | failed cleanup may accumulate large audio/video files |

---

# 7. Future Optimizations

Potential future improvements:
- GPU inference
- streaming diarization
- semantic transcript search
- vector embeddings
- transcript chunk batching
- optimized prompt engineering
- transcript chunk summarization

---

# Final Architecture Conclusion

The finalized architecture supports:
- upload transcription
- realtime caption streaming
- speaker-aware transcript generation
- structured transcript intelligence
- CPU-only deployment
- incremental persistence
- future scalability

All major technical feasibility risks were validated successfully during Phase 0 benchmarking and infrastructure testing.