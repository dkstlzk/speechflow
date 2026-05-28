# SpeechFlow Database Schema

Date: 27/05/2026

## Objective

Design a scalable PostgreSQL schema for:
- upload-based transcription sessions
- realtime streaming sessions
- transcript persistence
- speaker diarization storage
- summaries and action items
- future session history retrieval

The schema is designed specifically for:
- incremental transcript chunk storage
- asynchronous processing pipelines
- realtime caption persistence
- future frontend session history support

---

# Core Design Principles

- Every upload or live session is treated as a single session
- Transcripts are stored incrementally as chunks
- Speaker information is normalized into separate tables
- Summaries and intelligent outputs are generated post-processing
- Transcript ordering must rely on timestamps/chunk_index, not insertion order
- Upload and streaming pipelines share the same persistence model

---

# Table: sessions

Stores metadata for each upload or realtime streaming session.

## Purpose

Tracks:
- processing lifecycle
- upload vs streaming distinction
- overall session status
- timestamps
- duration
- frontend session history metadata

---

## Fields

| Field | Type | Description |
|---|---|---|
| id | UUID / SERIAL | Primary session identifier |
| session_type | TEXT | upload / streaming |
| status | TEXT | pending / transcribing / processing / complete / failed |
| original_filename | TEXT | uploaded file name |
| created_at | TIMESTAMP | session creation time |
| completed_at | TIMESTAMP | processing completion time |
| updated_at | TIMESTAMP | latest session update time |
| duration_seconds | FLOAT | total session duration |
| processing_error | TEXT / NULL | pipeline failure reason |

---

## Example

```json
{
  "id": 1,
  "session_type": "upload",
  "status": "complete",
  "original_filename": "meeting.mp4",
  "duration_seconds": 1854.2
}
```

---

# Table: transcript_chunks

Stores transcript segments generated incrementally from Whisper inference.

This is the core table of the entire system.

---

## Purpose

Supports:
- incremental persistence
- realtime streaming updates
- transcript reconstruction
- timestamp alignment
- speaker mapping
- frontend live caption rendering

---

## Fields

| Field | Type | Description |
|---|---|---|
| id | UUID / SERIAL | chunk identifier |
| session_id | FK | linked session |
| speaker_id | FK / NULL | linked speaker |
| start_time | FLOAT | transcript start timestamp |
| end_time | FLOAT | transcript end timestamp |
| text | TEXT | transcript text |
| chunk_index | INTEGER | ordering index |
| is_partial | BOOLEAN | indicates unstable streaming chunk |
| created_at | TIMESTAMP | persistence timestamp |

---

## Important Design Rule

Transcript reconstruction must ALWAYS use:

```sql
ORDER BY chunk_index
```

or timestamps.

Never rely on insertion order in async streaming systems.

---

## Example

```json
{
  "session_id": 1,
  "speaker_id": 2,
  "start_time": 12.4,
  "end_time": 15.1,
  "text": "Today we finalized the backend architecture.",
  "chunk_index": 14
}
```

---

# Table: speakers

Stores speaker identities detected during diarization.

---

## Purpose

Supports:
- speaker labeling
- frontend speaker coloring
- future speaker renaming
- transcript grouping

---

## Fields

| Field | Type | Description |
|---|---|---|
| id | UUID / SERIAL | speaker identifier |
| session_id | FK | linked session |
| speaker_label | TEXT | raw pyannote label |
| display_name | TEXT / NULL | optional user-facing name |

---

## Example

```json
{
  "speaker_label": "SPEAKER_00",
  "display_name": null
}
```

---

# Table: session_summary

Stores intelligent transcript outputs generated after processing.

---

## Purpose

Stores:
- summary
- minutes of meeting
- key discussion points
- post-processing outputs

---

## Fields

| Field | Type | Description |
|---|---|---|
| id | UUID / SERIAL | summary identifier |
| session_id | FK | linked session |
| summary | TEXT | generated summary |
| mom | JSON | structured MOM object |
| generated_at | TIMESTAMP | generation timestamp |

---

## Example

```json
{
  "summary": "Backend architecture finalized.",
  "mom": {
    "decisions": [],
    "next_steps": []
  }
}
```

---

# Table: action_items

Stores extracted action items from transcripts.

---

## Purpose

Supports:
- task extraction
- frontend task tracking
- future completion updates
- export generation

---

## Fields

| Field | Type | Description |
|---|---|---|
| id | UUID / SERIAL | action item identifier |
| session_id | FK | linked session |
| speaker_id | FK / NULL | linked speaker |
| task | TEXT | extracted task |
| deadline | TEXT / NULL | optional deadline |
| completed | BOOLEAN | completion status |

---

## Example

```json
{
  "task": "Implement upload endpoint",
  "completed": false
}
```

---

# Session Lifecycle

Typical lifecycle:

```text
pending
→ transcribing
→ processing
→ complete
```

Failure path:

```text
pending
→ failed
```

---

# Upload Pipeline Persistence Flow

```text
Upload
→ create session row
→ persist transcript chunks
→ persist speaker mappings
→ persist summary
→ persist action items
→ mark session complete
```

---

# Streaming Pipeline Persistence Flow

```text
WebSocket session starts
→ create session row
→ incremental transcript chunk persistence
→ partial caption updates
→ post-session diarization
→ summary generation
→ mark session complete
```

---

# Important Future Considerations

## Transcript Ordering

Streaming systems may:
- reorder packets
- reconnect sockets
- delay writes

Therefore:
- chunk_index is mandatory
- timestamps remain authoritative

---

## Speaker Alignment

Whisper timestamps must later be aligned against:
- pyannote speaker segments

Alignment logic will assign:
- transcript chunk
↔
- speaker identity

---

## Future Scalability

Future optimizations may include:
- transcript indexing
- vector embeddings
- semantic transcript search
- chunk batching
- archived session storage

---

# Final Architecture Decision

A chunk-based persistence architecture was selected because it supports:
- upload workflows
- realtime streaming workflows
- incremental caption updates
- future scalability
- speaker-aware transcript reconstruction