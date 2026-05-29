# Worker Lifecycle

Date: 28/05/2026

## Objective

Describe the threaded worker lifecycle used to process uploads without
blocking Flask request handlers.

## Upload Worker Flow

1. API receives upload and saves temp file.
2. API creates a session and returns session_id immediately.
3. Worker thread starts pipeline execution.
4. Worker updates session status after each stage.
5. Worker persists results and marks completion.

## Stage Transitions

pending -> preprocessing -> transcribing -> completed

Failure path:

pending -> failed

## Logging Requirements

- Log each stage transition with session_id.
- Log failures with stack traces and error details.
- Separate log namespaces for upload and worker modules.

## Stop Condition

This worker lifecycle intentionally stops before diarization and
post-processing logic. Phase 1 ends after transcription persistence.
