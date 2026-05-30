# Pipeline Flow

Date: 28/05/2026

## Objective

Define the finalized Phase 1 upload execution flow and transcript
reconstruction behavior.

## Phase 1 Upload Flow

`Upload -> temp file -> FFmpeg -> Whisper -> pyannote -> alignment -> persistence -> completed`

### Step-by-step

1. `POST /api/upload/` receives multipart audio and creates a session record.
2. File is saved to `TEMP_DIR`.
3. Worker thread starts and marks session `preprocessing`.
4. FFmpeg normalizes audio to 16kHz mono WAV.
5. Worker marks `transcribing` and runs faster-whisper.
6. Worker marks `diarizing` and runs pyannote diarization.
7. Alignment service maps Whisper segments to speaker intervals.
8. Worker marks `processing` and persists speaker-labeled chunks.
9. Session transitions to `completed`.

## Alignment Behavior (Final)

- Inputs are normalized and sorted deterministically.
- Speaker overlap is scored by total overlap per speaker label.
- Speaker switches require meaningful overlap strength.
- Tiny ambiguous overlaps use hysteresis to avoid rapid speaker jitter.
- Empty diarization output falls back to default speaker labeling.
- Single-speaker diarization remains stable across timestamp gaps.

## Persistence Behavior (Final)

- Transcript rows are persisted with fields:
  - `session_id`
  - `speaker_id`
  - `start_time`
  - `end_time`
  - `text`
  - `chunk_index`
  - `is_partial`
- Worker uses session-level chunk replacement on reruns to avoid duplicate
  transcript rows.

## Retrieval Flow

Endpoint:

`GET /api/sessions/<id>/transcript`

Response:

```json
{
  "session_id": "1",
  "status": "completed",
  "transcript": [
    {
      "speaker": "SPEAKER_00",
      "start": 0.0,
      "end": 1.0,
      "text": "hello",
      "order": 0
    }
  ]
}
```

Ordering rule for reconstruction:

`chunk_index -> start_time -> end_time -> row_id`

## Failure and Cleanup

- Any stage exception updates the session to `failed` with `processing_error`.
- Worker always executes cleanup for original upload and generated WAV artifacts.

## Phase Boundary

This flow intentionally stops at Phase 1 completion.

Not included here:

- Realtime websocket microphone streaming
- VAD-gated live chunking
- Summaries and action-item extraction
