# Worker Lifecycle

Date: 28/05/2026

## Objective

Describe the finalized threaded lifecycle used for Phase 1 upload processing.

## Worker Model

- Upload requests return quickly with `session_id`.
- Processing runs in daemon background threads.
- The worker owns stage transitions and persistence writes.

## Stage Transitions

Primary path:

`pending -> preprocessing -> transcribing -> diarizing -> processing -> completed`

Failure path:

`preprocessing|transcribing|diarizing|processing -> failed`

## Stage Responsibilities

1. `preprocessing`
- Convert source media into normalized WAV using FFmpeg.

2. `transcribing`
- Run faster-whisper and generate ordered transcript segments.

3. `diarizing`
- Run pyannote and produce speaker intervals.

4. `processing`
- Align transcript to diarization output.
- Resolve speaker IDs.
- Persist speaker-labeled transcript chunks.

5. `completed`
- Mark lifecycle completion and make retrieval available.

## Failure Handling

- Any unhandled exception marks the session `failed`.
- Error details are written to `processing_error`.
- Failure logging includes `session_id` context.

## Cleanup Guarantees

Worker always attempts cleanup in `finally`:

- uploaded temp file
- preprocessed WAV artifact

This applies to both successful and failed runs.

## Determinism and Safety

- Alignment is deterministic for the same transcript and diarization inputs.
- Transcript persistence is replacement-based per session to prevent duplicate
  chunk accumulation on retries.
- Retrieval order is deterministic and reproducible.

## Phase Boundary

Worker lifecycle for Phase 1 ends after transcript persistence and completion.
No streaming, summarization, or Phase 2 orchestration is triggered here.
