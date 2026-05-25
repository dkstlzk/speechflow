# SpeechFlow

SpeechFlow is a full-stack AI-powered speech-to-text and intelligent transcript processing system built using fully local, open-source models.

The system supports:
- Real-time microphone transcription
- MP3/MP4 upload-based transcription
- Speaker-aware transcript generation
- Transcript persistence and session management
- Post-session transcript intelligence:
  - Summary generation
  - MOM (Minutes of Meeting) generation
  - Action item extraction

The MVP is designed as a CPU-only, backend-first architecture focused on functional correctness, real-time processing, and structured conversational intelligence.

## Core Features

### Real-Time Transcription
- Browser microphone streaming
- Live caption generation
- WebSocket-based streaming pipeline
- Incremental transcript persistence

### Upload-Based Transcription
- MP3/MP4 upload support
- Audio extraction and normalization
- Timestamped transcript generation
- Speaker diarization

### Intelligent Transcript Processing
- AI-generated conversation summaries
- Structured MOM generation
- Action item/task extraction
- Speaker-attributed transcript intelligence

## Tech Stack

### Backend
- FastAPI
- PostgreSQL
- WebSockets
- FFmpeg
- Pydub

### Speech & Audio
- faster-whisper
- pyannote.audio
- Silero VAD

### Intelligent Processing
- Ollama
- phi3:mini / llama3.2

### Frontend
- React + Vite

## Constraints
- CPU-only development
- No hosted STT APIs
- Open-source local models only
- English-only MVP

## Project Status
Currently in active MVP development.