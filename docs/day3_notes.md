# Day 3 Notes — Architecture & Backend Design

Date: 27/05/2026

---

# Objective

Focused on finalizing the complete backend architecture and persistence design before beginning Phase 1 implementation.

The primary goal was to:
- finalize database schema design
- define backend service boundaries
- design transcript persistence structures
- finalize upload and streaming execution flows
- prepare scalable backend project architecture

---

# Completed Today

## Database Architecture

Designed complete PostgreSQL schema architecture for:
- sessions
- transcript_chunks
- speakers
- session_summary
- action_items

Finalized:
- chunk-based transcript persistence strategy
- session lifecycle states
- streaming-safe transcript ordering
- speaker mapping structure
- summary and action-item persistence model

Key architecture decisions:
- upload and streaming pipelines share unified persistence layer
- transcript reconstruction based on timestamps + chunk_index
- speaker data normalized into separate tables
- summaries stored separately from raw transcript chunks

---

## Transcript Structure Design

Designed standardized transcript data structures for:
- finalized transcript chunks
- realtime partial transcript updates
- streaming chunk persistence
- frontend/API response formatting

Defined:
- transcript chunk JSON format
- partial streaming caption structure
- final session response structure
- transcript-speaker alignment format

Additional considerations:
- future confidence score support
- scalable export compatibility
- frontend-friendly transcript rendering

---

## Pipeline Architecture Finalization

Finalized complete execution architecture for both:
- upload processing pipeline
- realtime streaming pipeline

Upload pipeline finalized as:

```text
Upload
→ temp file save
→ FFmpeg preprocessing
→ Whisper transcription
→ speaker segmentation
→ transcript-speaker alignment
→ transcript persistence
→ summary generation
→ action extraction
```

Streaming pipeline finalized as:

```text
Browser microphone
→ MediaRecorder chunks
→ WebSocket streaming
→ backend ring buffer
→ Silero VAD
→ rolling Whisper inference
→ incremental persistence
→ post-session diarization
→ summary generation
```

---

# Backend Service Architecture

Prepared scalable backend folder structure:

```text
backend/app/
├── routers/
├── services/
├── models/
├── schemas/
├── db/
├── utils/
```

Defined responsibilities for:
- routers
- service layer
- DB layer
- transcript reconstruction logic
- preprocessing utilities
- streaming orchestration

---

# Key Technical Decisions

## Chunk-Based Persistence

Selected incremental chunk storage instead of monolithic transcripts to support:
- realtime streaming
- partial updates
- scalable persistence
- transcript synchronization
- future semantic search support

---

## Post-Session Diarization

Realtime diarization intentionally deferred until after streaming session completion due to:
- CPU-only deployment constraints
- pyannote latency concerns
- memory pressure risks

---

## WAV as Internal Audio Standard

Standardized internal processing format as:

```text
16kHz mono WAV
```

for:
- stable Whisper inference
- consistent preprocessing
- simplified downstream handling

---

## Async-Oriented Backend Design

FastAPI async architecture selected to support:
- long-running inference tasks
- concurrent uploads
- WebSocket streaming
- incremental transcript updates

---

# Risks Identified

- pyannote latency on long recordings
- CPU memory pressure during simultaneous Whisper + Ollama execution
- transcript synchronization edge cases during rolling inference
- temp file accumulation risk without cleanup
- future long-session summarization chunking complexity

---

# Documentation Created

Created:
- db_schema.md
- transcript_structure.md
- pipeline_architecture.md

Updated:
- README.md
- .gitignore

---

# Current Status

Phase 0 architecture and backend planning completed successfully.

Infrastructure, benchmarking, persistence design, and execution architecture are now finalized and implementation-ready.

---

# Next Phase

Beginning Phase 1:
- upload transcription backend implementation
- FastAPI upload endpoints
- FFmpeg preprocessing service
- Whisper transcription integration
- transcript persistence workflow
- database integration