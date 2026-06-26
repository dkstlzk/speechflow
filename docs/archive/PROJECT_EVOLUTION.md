# SpeechFlow Project Evolution

This document serves as the "engineering story" of SpeechFlow, documenting the chronological evolution of the system's architecture, the problems encountered at each stage, and the implemented solutions.

---

## Phase 1: Upload Pipeline

**Problem**
The initial requirement was to process static audio and video files locally without relying on expensive cloud APIs. We needed a robust way to extract audio, normalize it, and transcribe it using local CPU resources.

**Solution**
We built a Flask backend that accepted MP3 and MP4 uploads. FFmpeg was integrated to extract the 16kHz mono audio required by speech models. We integrated `faster-whisper` for the core transcription and structured the database using SQLAlchemy to store the resulting text.

**Key Commits**
* *(Pre-5f5900a)* Initial repository setup and batch processing scripts.

**Outcome**
A functional, albeit slow, batch processing pipeline that successfully transcribed static files and saved them to PostgreSQL.

---

## Phase 2: Intelligence Layer

**Problem**
Raw transcripts are difficult to read. We needed a way to derive value from the text, such as summarizing long meetings and extracting action items, while maintaining the "local-only" privacy requirement.

**Solution**
We integrated the Ollama framework running the `qwen2.5:3b` model. We built an intelligence pipeline that hooked into the finalization of the upload process. The pipeline chunked long transcripts, executed map-reduce style summarization, and ran targeted prompts to extract Action Items and Meeting Minutes (MoM).

**Key Commits**
* `5f5900a` - Phase 2 integration complete and working

**Outcome**
The system could now not only transcribe but comprehend the audio. However, it was strictly limited to pre-recorded files, lacking any live capabilities.

---

## Phase 3: Realtime Transport

**Problem**
Users needed to transcribe live meetings, not just upload recordings after the fact. The HTTP request/response model was entirely incapable of handling a continuous stream of audio bytes.

**Solution**
We migrated the architecture to an event-driven model using `Flask-SocketIO`. On the frontend, we tapped into the browser's `AudioContext` and implemented an `AudioWorkletNode` to capture raw PCM audio and pipe it directly over the WebSocket in tiny binary chunks.

**Key Commits**
* `2bd91a5` - establish phase 3 real-time socket.io transport
* `467e63d` - establish end-to-end audio streaming infrastructure

**Outcome**
We achieved a low-latency, bidirectional data pipe capable of moving raw audio from the user's microphone directly into Flask's memory.

---

## Phase 3.1: Live Whisper

**Problem**
With raw bytes streaming in, we needed a way to transcribe them on the fly. However, running Whisper on every 1-second chunk resulted in massive hallucinations because the model lacked acoustic context.

**Solution**
We implemented a background worker thread and a "Rolling Acoustic Context" buffer. The transcriber always looks at a sliding window of the last X seconds of audio, providing Whisper with enough momentum to accurately guess the current words. We then implemented a Delta Stabilization algorithm to diff the transcripts, isolating the "stable" words from the "tentative" trailing edge.

**Key Commits**
* `2e5dc43` - implement live whisper inference
* `8fdc289` - implement transcript delta detection

**Outcome**
The frontend could now display a fluid, live-updating transcript where tentative guesses gracefully resolved into solid text as the speaker finished their sentence.

---

## Phase 3.2: VAD Segmentation

**Problem**
The rolling buffer couldn't grow infinitely without crashing the server's RAM. We needed a way to intelligently chop the infinite stream into discrete, permanent chunks.

**Solution**
We integrated Silero VAD (Voice Activity Detection). Instead of chopping the audio arbitrarily every 30 seconds (which cuts words in half), VAD monitors the stream for acoustic silence. When a user pauses speaking for >500ms, VAD triggers a boundary. The buffer up to that boundary is finalized and flushed from RAM.

**Key Commits**
* `c42baab` - integrate silero vad for acoustic silence detection

**Outcome**
Infinite streams were successfully transformed into a sequence of discrete, perfectly sliced conversational sentences.

---

## Phase 3.3: Transcript Persistence

**Problem**
The live transcripts existed purely in the UI and Flask RAM. If the browser refreshed, the entire meeting was lost.

**Solution**
We mapped the VAD boundaries to database commits. Whenever VAD closed a chunk, it was marked "Committed", injected with precise `start_time` and `end_time` metadata relative to the session start, and flushed to PostgreSQL. We also tied the Phase 2 Intelligence layer to trigger autonomously once the realtime session completed.

**Key Commits**
* `35f6259` - add VAD-driven chunk commits and transcript persistence
* `d538fc8` - persist transcript classification

**Outcome**
Realtime sessions became permanent, enabling playback timelines and AI summarization for live meetings.

---

## Phase 3.4: Lovable UI Merge

**Problem**
The application possessed incredible backend logic but looked like a barebones MVP. It lacked polish, loading states, and a cohesive design system.

**Solution**
We utilized Lovable to generate a modern, glass-morphic React redesign. We painstakingly merged our complex WebSocket hooks, audio capture logic, and state management into the new aesthetic components. 

**Key Commits**
* `7a69910` - Redesigned SpeechFlow UI
* `0947ddb` - combine lovable ui redesign with realtime architecture

**Outcome**
SpeechFlow evolved into a premium, trustworthy product visually commensurate with its underlying technology.

---

## Phase 3.5: Reliability Hardening

**Problem**
Running heavy AI inference inside multithreaded WebSocket applications caused severe instability. We experienced race conditions, deadlocks where the UI froze, and "zombie sessions" where the backend failed to finalize a meeting if the user closed their laptop unexpectedly.

**Solution**
We modularized the massive `worker.py` file, aggressively narrowed the scope of `session.lock` to prevent blocking the ingestion threads, and built a self-healing Watchdog. The Watchdog actively monitors `last_activity_time` and forces cleanup if a socket dies silently. We also implemented strict hardware teardown (`track.stop()`) to protect user privacy when paused.

**Key Commits**
* `10f2f3b` - serialize transcription ownership and narrow lock scope
* `026a344` - harden session finalization, watchdog recovery and microphone lifecycle

**Outcome**
The pipeline became virtually crash-proof, natively recovering from network drops, browser kills, and unexpected hardware suspensions.

---

## Phase 3.6: Session Isolation Architecture

**Problem**
If a user rapidly started and stopped recordings, delayed audio packets from the older, dead session would arrive at the server and accidentally append themselves to the brand-new session, creating a corrupted, merged transcript.

**Solution**
We implemented strict UUID ownership. The frontend now binds an immutable `sessionId` to every WebSocket packet. The backend strictly drops any packet whose ID does not match the active recording. Furthermore, the backend `session_manager` aggressively pops old dictionaries, explicitly severing them from memory.

**Key Commits**
* `b6d141a` - harden session lifecycle and transcript isolation

**Outcome**
Absolute data integrity. Parallel and rapidly sequential sessions are mathematically isolated from one another.
