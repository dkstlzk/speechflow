# Database Schema

Date: 09/06/2026

## Objective

Capture the finalized persistence model used by SpeechFlow, supporting both the upload transcription pipeline and the real-time intelligence generation flows.

## Design Principles

- Session-centric lifecycle tracking.
- Ordered chunk persistence for deterministic reconstruction.
- Intelligence generation artifacts (Summaries, Action Items) linked directly to sessions.
- PostgreSQL GIN indexing for Full Text Search (FTS) across transcript chunks.

## Table: `sessions`

Tracks upload and real-time lifecycle state.

| Field | Type | Notes |
| --- | --- | --- |
| `id` | SERIAL / INTEGER | Primary key |
| `session_type` | VARCHAR(32) | `upload` or `realtime` |
| `status` | ENUM(`session_status`) | Lifecycle status |
| `original_filename` | VARCHAR(255) | Uploaded filename |
| `audio_path` | VARCHAR(255) | Server-side WAV storage path |
| `duration_seconds` | FLOAT | Total audio duration |
| `processing_error` | TEXT | Failure detail |
| `title` | VARCHAR(255) | Auto-generated or user-edited title |
| `host_name` | VARCHAR(255) | Optional host name |
| `participants` | TEXT | Optional participants list |
| `classification` | VARCHAR(50) | Intelligence classification (e.g. `meeting`, `lecture`) |
| `diarization_mode` | VARCHAR(32) | Track quick vs accurate execution |
| `diarized_at` | DATETIME | Timestamp of last diarization |
| `detected_language` | VARCHAR(10) | Primary spoken language detected |
| `detected_languages` | JSON | Extended language metadata |
| `sample_rate` | INTEGER | Persisted sample rate for recovery |
| `transcript_type` | VARCHAR(32) | Native vs translated transcript tracking |
| `created_at` | TIMESTAMP | Created timestamp |
| `updated_at` | TIMESTAMP | Last update timestamp |
| `completed_at` | TIMESTAMP | Completion/failure timestamp |

Session Status Enum:

`pending, preprocessing, transcribing, diarizing, processing, completed, failed, recording, finalizing`

## Table: `speakers`

Stores diarization labels per session.

| Field | Type | Notes |
| --- | --- | --- |
| `id` | SERIAL / INTEGER | Primary key |
| `session_id` | FK -> sessions.id | Session scope |
| `speaker_label` | VARCHAR(64) | e.g. `SPEAKER_00` |
| `display_name` | VARCHAR(255) | Optional user-defined alias |

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
| `is_partial` | BOOLEAN | Indicates tentative realtime chunks |
| `search_vector` | TSVECTOR | Auto-updating FTS indexing field |
| `created_at` | TIMESTAMP | Insert timestamp |

**FTS Note:** A GIN index exists on `search_vector`, utilizing `to_tsvector('english', text)` to enable rapid full-text search across all transcripts.

## Table: `summaries`

Stores auto-generated intelligence summaries and Meeting Minutes (MoM).

| Field | Type | Notes |
| --- | --- | --- |
| `id` | SERIAL / INTEGER | Primary key |
| `session_id` | FK -> sessions.id | Session scope |
| `summary_text` | TEXT | Executive summary content |
| `mom_text` | TEXT | Structured Meeting Minutes content |
| `created_at` | TIMESTAMP | Creation timestamp |
| `updated_at` | TIMESTAMP | Last update timestamp |

## Table: `action_items`

Stores extracted action items.

| Field | Type | Notes |
| --- | --- | --- |
| `id` | SERIAL / INTEGER | Primary key |
| `session_id` | FK -> sessions.id | Session scope |
| `description` | TEXT | The action task |
| `assignee` | VARCHAR(255) | Nullable extracted assignee |
| `status` | VARCHAR(50) | `pending` or `completed` |
| `created_at` | TIMESTAMP | Creation timestamp |
| `updated_at` | TIMESTAMP | Last update timestamp |

## Table: `session_translations`

Stores fully translated sessions, tracking their status and content.

| Field | Type | Notes |
| --- | --- | --- |
| `id` | SERIAL / INTEGER | Primary key |
| `session_id` | FK -> sessions.id | Session scope |
| `target_language` | VARCHAR(10) | e.g. `hi`, `ta`, `fr` |
| `status` | VARCHAR(32) | `translating`, `completed`, `failed`, `invalidated` |
| `translated_summary` | TEXT | Translated executive summary |
| `translated_mom` | TEXT | Translated MoM |
| `error_message` | TEXT | Detailed error logs |
| `created_at` | TIMESTAMP | Creation timestamp |
| `updated_at` | TIMESTAMP | Last update timestamp |

## Table: `translated_chunks`

Stores the translated text mapping to the original transcript chunks.

| Field | Type | Notes |
| --- | --- | --- |
| `id` | SERIAL / INTEGER | Primary key |
| `translation_id` | FK -> session_translations.id | Translation scope |
| `chunk_id` | FK -> transcript_chunks.id | Original chunk mapping |
| `translated_text` | TEXT | Translated text |
| `created_at` | TIMESTAMP | Creation timestamp |

## Ordering Contract

Transcript reconstruction query ordering:

`ORDER BY chunk_index, start_time, end_time, id`

This guarantees deterministic retrieval for API consumers.

## Persistence Contract

- Worker persists speaker-labeled transcript chunks after alignment.
- On rerun/retry, chunk rows are replaced per session before insert to avoid duplicates.
- Real-time chunks are appended incrementally; the final cleanup merges overlapping chunks.
- Session status changes are committed at each stage transition, utilizing isolated Database connections for reliable `FAILED` state transitions on errors.
- Intelligence generation explicitly wraps `OllamaClientError` to prevent DB poisoning.
