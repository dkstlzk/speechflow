# Database Schema

Date: 28/05/2026

## Objective

Define a PostgreSQL schema that supports upload and streaming sessions,
chunk-based transcript persistence, diarization, and post-session
intelligence outputs.

## Core Design Principles

- Each upload or streaming run is a session.
- Transcripts are stored incrementally as ordered chunks.
- Chunk ordering relies on chunk_index or timestamps, not insertion order.
- Upload and streaming pipelines share the same persistence model.

## Table: sessions

Tracks upload and streaming session lifecycle.

| Field | Type | Description |
| --- | --- | --- |
| id | SERIAL | Primary key |
| session_type | TEXT | upload or streaming |
| status | TEXT | pending, uploaded, preprocessing, transcribing, diarizing, processing, completed, failed |
| original_filename | TEXT | uploaded filename (nullable) |
| created_at | TIMESTAMP | session creation time |
| updated_at | TIMESTAMP | last update time |
| completed_at | TIMESTAMP | completion time (nullable) |
| duration_seconds | FLOAT | total duration (nullable) |
| processing_error | TEXT | error details (nullable) |

## Table: transcript_chunks

Stores transcript segments from Whisper inference.

| Field | Type | Description |
| --- | --- | --- |
| id | SERIAL | Primary key |
| session_id | FK | sessions.id |
| speaker_id | FK | speakers.id (nullable) |
| start_time | FLOAT | segment start time |
| end_time | FLOAT | segment end time |
| text | TEXT | transcript text |
| chunk_index | INTEGER | ordering index |
| is_partial | BOOLEAN | partial streaming flag |
| created_at | TIMESTAMP | persistence time |

Ordering rule:

```sql
ORDER BY chunk_index
```

## Table: speakers

Speaker identities detected by diarization.

| Field | Type | Description |
| --- | --- | --- |
| id | SERIAL | Primary key |
| session_id | FK | sessions.id |
| speaker_label | TEXT | raw pyannote label |
| display_name | TEXT | optional rename |

## Table: session_summaries

Stores summary and MOM payloads.

| Field | Type | Description |
| --- | --- | --- |
| id | SERIAL | Primary key |
| session_id | FK | sessions.id |
| summary | TEXT | generated summary |
| mom | JSON | structured MOM object |
| created_at | TIMESTAMP | generation time |

## Table: action_items

Stores action items extracted from sessions.

| Field | Type | Description |
| --- | --- | --- |
| id | SERIAL | Primary key |
| session_id | FK | sessions.id |
| text | TEXT | extracted task |
| status | TEXT | open or done |
| created_at | TIMESTAMP | creation time |

## Indexing Guidance

- transcript_chunks(session_id, chunk_index)
- speakers(session_id)
- action_items(session_id)
- session_summaries(session_id)

## Persistence Notes

- Streaming persists partial chunks with is_partial=true.
- Finalization overwrites or supersedes partial chunks.
- Session status transitions are updated on each pipeline stage.

## Status Enumeration

Statuses are centralized in models/enums.py for reuse across API, workers,
and repositories.

Phase 1 uses the subset:

pending -> preprocessing -> transcribing -> completed (or failed)
