# Day 2 Notes — Phase 0
Date: 26/05/2026

## Objective
Continue Phase 0 validation by benchmarking inference behavior, validating speaker diarization on real audio, researching streaming architecture requirements, and finalizing upload + realtime pipeline decisions before backend implementation.

---

## 1. pyannote Speaker Diarization Validation

Validated pyannote.audio speaker diarization locally on CPU using:
- pyannote/speaker-diarization-3.1
- HuggingFace gated model authentication
- local WAV audio samples

Tested diarization on multi-speaker audio converted from MP4 to WAV.

Observed:
- successful speaker segmentation
- diarization inference completed locally without crashes
- multiple speaker clusters detected successfully
- occasional over-segmentation into extra speaker IDs observed
- behavior acceptable for MVP feasibility

Sample output:
- SPEAKER_00
- SPEAKER_01
- SPEAKER_02

Inference warnings related to PyTorch std() appeared but did not affect functionality.

Conclusion:
Post-session speaker diarization is feasible locally on CPU using pyannote.audio. Additional alignment and cluster cleanup logic may be required later for production-quality speaker labeling.

---

## 2. phi3:mini Longer Transcript Benchmark

Benchmarked Ollama + phi3:mini using longer meeting-style transcript prompts.

Tested:
- meeting summary generation
- key decisions extraction
- action item extraction
- risk extraction

Observed:
- coherent structured outputs
- action items extracted reliably
- risk extraction worked correctly
- outputs occasionally overly verbose
- repeated technical details observed
- first-token response latency approximately 15 seconds
- full completion time significantly longer due to verbose generation

Measured runtime:
- full completion ≈ 3m39s in interactive terminal mode

Conclusion:
Local transcript intelligence pipeline is feasible using Ollama + phi3:mini, though prompt optimization and transcript chunking strategies will be required later to reduce verbosity and improve response speed.

---

## 3. Whisper + Ollama Concurrent Execution Test

Tested simultaneous execution of:
- faster-whisper inference
- Ollama phi3:mini inference

System monitoring performed using htop.

Observed:
- system remained stable during concurrent inference
- CPU load distributed across multiple cores
- no crashes or major UI freezing observed
- significant RAM usage increase under concurrent workloads
- swap memory usage triggered during simultaneous inference

Approximate observations:
- RAM usage ≈ 11–12 GB
- swap usage observed
- CPU utilization remained high but stable

Conclusion:
Concurrent local inference is feasible for MVP requirements, but realtime streaming architecture should prioritize Whisper-only inference during active sessions. Summarization and diarization are better handled post-session to reduce CPU and memory pressure.

---

## 4. Audio Format Comparison

Compared transcription behavior across:
- WAV
- MP3
- MP4

Benchmark observations:
- WAV inference ≈ 5.79s
- MP3 inference ≈ 5.23s
- MP4 inference ≈ 4.85s

Observed:
- all formats produced acceptable transcription quality
- latency differences remained relatively small after model warmup
- MP4 required preprocessing/demuxing overhead
- WAV remained the most stable inference format
- all tested formats still achieved faster-than-realtime transcription on CPU

Conclusion:
All uploaded and streamed audio should be normalized internally into mono 16kHz WAV before Whisper inference for consistency and stability.

---

## 5. FastAPI Async Architecture Research

Studied:
- async def
- await
- non-blocking request handling
- UploadFile
- concurrency behavior
- BackgroundTasks basics

Understanding:
FastAPI async endpoints allow non-blocking handling of uploads, WebSocket streams, and long-running inference tasks, making them suitable for concurrent transcription sessions.

Conclusion:
FastAPI async architecture is appropriate for both upload-based and realtime streaming pipelines.

---

## 6. FastAPI WebSocket Lifecycle Research

Studied:
- websocket.accept()
- websocket.receive_bytes()
- websocket.send_text()
- disconnect handling
- async receive loops

Understanding:
Realtime streaming will use:
Browser microphone
→ MediaRecorder audio chunks
→ FastAPI WebSocket receive loop
→ rolling backend inference
→ incremental caption updates to frontend

Conclusion:
FastAPI WebSockets are sufficient for MVP realtime caption streaming architecture.

---

## 7. MediaRecorder + Streaming Format Research

Researched browser-side audio chunk generation using MediaRecorder API.

Studied:
- WebM/Opus
- WAV/PCM
- browser chunk streaming behavior

Architecture decision:
- browser microphone audio will use MediaRecorder-generated WebM/Opus chunks
- backend preprocessing will convert chunks internally into WAV/PCM before Whisper inference

Conclusion:
WebM/Opus chosen for frontend streaming due to browser compatibility and efficient chunk transport.

---

## 8. Upload Pipeline Architecture Finalization

Finalized upload transcription pipeline:

MP3/MP4 Upload
→ FastAPI Upload Endpoint
→ Temporary File Storage
→ FFmpeg Audio Normalization
→ 16kHz Mono WAV
→ faster-whisper Transcription
→ pyannote Speaker Diarization
→ Transcript Alignment
→ PostgreSQL Persistence
→ Ollama Summarization + Action Extraction
→ API Response

Conclusion:
Upload pipeline architecture finalized for implementation phase.

---

## 9. Realtime Streaming Architecture Finalization

Finalized realtime streaming architecture:

Browser Microphone
→ MediaRecorder WebM/Opus Chunks
→ WebSocket Streaming
→ Backend Ring Buffer
→ FFmpeg Conversion
→ Silero VAD Gating
→ Rolling Whisper Inference
→ Incremental Caption Updates
→ PostgreSQL Persistence
→ Post-session Diarization
→ Ollama Summarization

Conclusion:
Realtime streaming architecture finalized for MVP implementation.

---

## 10. Overall Day 2 Conclusions

Key Findings:
- Local CPU-only deployment remains feasible
- faster-whisper performance exceeds realtime requirements
- pyannote diarization functional locally
- Ollama summarization functional but requires prompt optimization
- simultaneous inference possible but memory-intensive
- post-session summarization/diarization architecture justified
- upload and streaming pipeline architectures finalized

Current Status:
Core technical feasibility, architecture validation, and infrastructure benchmarking completed successfully for Phase 0.