# SpeechFlow

SpeechFlow is a full-stack speech-to-text and intelligent transcript processing system focused on realtime and upload-based conversational transcription.

The system supports:
- realtime microphone transcription
- MP3/MP4 upload transcription
- speaker-aware transcript generation
- transcript persistence and session history
- AI-generated summaries and structured meeting insights

The MVP is designed as a CPU-first, backend-oriented architecture prioritizing:
- functional correctness
- realtime feasibility
- scalable transcript persistence
- structured conversational intelligence

---

# Core Features

## Realtime Streaming Transcription

- Browser microphone streaming
- WebSocket-based audio transport
- Rolling Whisper inference
- Live caption generation
- Incremental transcript persistence
- Post-session speaker diarization

---

## Upload-Based Transcription

- MP3 / WAV / MP4 upload support
- FFmpeg preprocessing pipeline
- Audio normalization (16kHz mono WAV)
- Timestamped transcript generation
- Speaker-aware transcript reconstruction

---

## Intelligent Transcript Processing

- Meeting summary generation
- Minutes of Meeting (MOM)
- Action item extraction
- Structured conversational insights

---

# Tech Stack

## Backend

- FastAPI
- PostgreSQL
- WebSockets
- SQLAlchemy
- FFmpeg

---

## Speech & Audio
- faster-whisper
- pyannote.audio
- Silero VAD

---

## Intelligent Processing

- Ollama
- phi3:mini

---

## Frontend

- React
- Vite

---

# System Architecture

## Upload Pipeline

```text
Upload
→ FFmpeg preprocessing
→ Whisper transcription
→ Speaker segmentation
→ Transcript-speaker alignment
→ Transcript persistence
→ Summary + action extraction
```

---

## Streaming Pipeline

```text
Browser microphone
→ MediaRecorder chunks
→ WebSocket streaming
→ Backend ring buffer
→ Silero VAD
→ Rolling Whisper inference
→ Incremental transcript persistence
→ Post-session diarization
→ Summary generation
```

---

# Current Project Status

Current Phase:
- Phase 0 completed
- infrastructure validation completed
- CPU feasibility benchmarking completed
- backend architecture finalized

Upcoming Work:
- upload transcription APIs
- transcript persistence layer
- realtime WebSocket pipeline
- frontend integration

---

# Current Repository Structure

```text
speechflow/
│
├── backend/
│   ├── app/
│   │   ├── db/
│   │   ├── models/
│   │   ├── routers/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── utils/
│   │   └── main.py
│   │
│   ├── docs/
│   └── tests/
│
├── docs/
├── frontend/
├── ml_models/
├── temp/
├── test_audio/
├── transcripts/
├── exports/
│
├── README.md
├── LICENSE
├── pyproject.toml
└── .gitignore
```

---

# Backend Architecture

## Routers

API layer only:
- upload routes
- websocket routes
- session APIs
- action item APIs

---

## Services

Core business logic:
- Whisper inference
- diarization
- transcript alignment
- FFmpeg preprocessing
- streaming orchestration
- summary generation

---

## Database Layer

Handles:
- session persistence
- transcript chunk storage
- speaker mappings
- summaries
- action items

---

# Constraints

- CPU-only development
- local inference only
- English-only MVP
- realtime latency target: 4–6 seconds

---

# Future Improvements

Planned future enhancements:
- GPU acceleration
- semantic transcript search
- vector embeddings
- streaming diarization
- transcript export formats
- speaker renaming
- long-session optimization

---

# License

MIT License