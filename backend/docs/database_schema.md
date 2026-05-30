# Database Schema

Date: 28/05/2026

## Objective

Capture the finalized persistence model used by the Phase 1 upload
transcription pipeline.

## Design Principles

- Session-centric lifecycle tracking.
- Ordered chunk persistence for deterministic reconstruction.
- Speaker labels persisted separately and referenced by transcript chunks.
- Repository-layer writes and reads enforce stable ordering behavior.

## Table: `sessions`

Tracks upload lifecycle state.

| Field | Type | Notes |
| --- | --- | --- |
| `id` | SERIAL / INTEGER | Primary key |
| `session_type` | VARCHAR(32) | `upload` for Phase 1 |
| `status` | ENUM(`session_status`) | Lifecycle status |
| `original_filename` | VARCHAR(255) | Uploaded filename |
| `duration_seconds` | FLOAT | Optional |
| `processing_error` | TEXT | Failure detail |
| `created_at` | TIMESTAMP | Created timestamp |
| `updated_at` | TIMESTAMP | Last update timestamp |
| `completed_at` | TIMESTAMP | Completion/failure timestamp |

Phase 1 status subset:

`pending, preprocessing, transcribing, diarizing, processing, completed, failed`

## Table: `speakers`

Stores diarization labels per session.

| Field | Type | Notes |
| --- | --- | --- |
| `id` | SERIAL / INTEGER | Primary key |
| `session_id` | FK -> sessions.id | Session scope |
| `speaker_label` | VARCHAR(64) | e.g. `SPEAKER_00` |
| `display_name` | VARCHAR(255) | Optional alias |

Repository behavior normalizes empty labels to `UNKNOWN`.

## Table: `transcript_chunks`

Stores final transcript chunks with speaker references.

| Field | Type | Notes |
| --- | --- | --- |
| `id` | SERIAL / INTEGER | Primary key |
| `session_id` | FK -> sessions.id | Session scope |
| `speaker_id` | FK -> speakers.id | Nullable fallback supported |
| `start_time` | FLOAT | Segment start |
| `end_time` | FLOAT | Segment end |
| `text` | TEXT | Chunk text |
| `chunk_index` | INTEGER | Chunk order index |
| `is_partial` | BOOLEAN | Reserved for streaming phases |
| `created_at` | TIMESTAMP | Insert timestamp |

## Ordering Contract

Transcript reconstruction query ordering:

`ORDER BY chunk_index, start_time, end_time, id`

This guarantees deterministic retrieval for API consumers.

## Persistence Contract

- Worker persists speaker-labeled transcript chunks after alignment.
- On rerun/retry, chunk rows are replaced per session before insert to avoid
  duplicates.
- Session status changes are committed at each stage transition.

## Retrieval Contract

`GET /api/sessions/<id>/transcript` returns:

- `session_id`
- `status`
- ordered `transcript` chunk list with speaker labels

## Phase Boundary

Schema supports future phases, but Phase 1 closure is limited to upload,
transcription, diarization, alignment, and transcript retrieval.
