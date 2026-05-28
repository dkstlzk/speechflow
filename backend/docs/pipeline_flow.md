# Pipeline Flow

Date: 28/05/2026

## Objective

Provide a detailed, implementation-ready reference for upload and streaming
pipelines, including transcript structures and SocketIO event contracts.

## Upload Pipeline

Flow:

Upload -> temp file -> FFmpeg normalize -> Whisper -> diarization
-> transcript alignment -> persistence -> summarization -> session complete

Step-by-step:

1. Receive multipart upload and create a session row.
2. Save the file into temp/ for preprocessing.
3. Normalize to 16kHz mono WAV using FFmpeg.
4. Run faster-whisper on the normalized WAV.
5. Run pyannote diarization on the full audio file.
6. Align Whisper segments with diarization regions.
7. Persist transcript chunks and speaker mappings.
8. Run summary, MOM, and action item extraction.
9. Mark the session complete and return session_id.

## Realtime Streaming Pipeline

Flow:

MediaRecorder -> SocketIO -> rolling buffer + VAD -> rolling Whisper
-> partial transcript persistence -> stream end -> diarization -> summary

Step-by-step:

1. Client opens SocketIO connection and emits stream_start.
2. Server creates a streaming session and prepares the rolling buffer.
3. Client emits audio_chunk events at a fixed interval.
4. Server appends chunks to buffer and runs VAD gating.
5. Rolling Whisper inference yields partial transcript chunks.
6. Server emits partial_transcript updates for live captions.
7. Client emits stream_end to finalize the session.
8. Server runs diarization, summarization, and final persistence.

## SocketIO Event Contract

Client -> Server:

- stream_start: begins a streaming session.
  - payload: session metadata, sample_rate, channel_count
- audio_chunk: raw audio bytes plus chunk_index.
- stream_end: finalize streaming session.

Server -> Client:

- stream_ack: session started.
  - payload: session_id
- partial_transcript: rolling caption updates.
  - payload: chunk_index, text, partial=true
- stream_complete: session finalized.
  - payload: session_id

## Rolling Window Guidance

- Use short chunks (500ms to 1s) for low latency.
- Keep a rolling window of 10s to 20s for context.
- Persist partial chunks with is_partial=true, then overwrite on finalize.

## Transcript Structures

Final transcript chunk:

```json
{
  "speaker": "SPEAKER_00",
  "start": 12.5,
  "end": 15.8,
  "text": "Today we finalized the backend architecture.",
  "confidence": null
}
```

Partial streaming chunk:

```json
{
  "partial": true,
  "chunk_index": 14,
  "text": "Today we finalized",
  "timestamp": 1716812
}
```

Final session response:

```json
{
  "session_id": 1,
  "status": "complete",
  "transcript": [],
  "summary": "",
  "mom": {
    "attendees": [],
    "key_points": [],
    "decisions": [],
    "next_steps": []
  },
  "action_items": []
}
```

## Session Lifecycle

pending -> transcribing -> processing -> complete

Failure path:

pending -> failed

## Cleanup and Failure Handling

- Always delete temp files after success or failure.
- Store processing_error on session failure for debugging.
- Persist partial chunks during streaming and finalize after diarization.
