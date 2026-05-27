# SpeechFlow Transcript Structures

Date: 27/05/2026

## Objective

Define standardized transcript-related data structures for:
- upload transcription
- realtime streaming
- speaker diarization
- frontend rendering
- database persistence
- API responses

These structures are designed to remain consistent across:
- Whisper inference
- pyannote diarization
- PostgreSQL storage
- WebSocket streaming
- frontend consumption
- export pipelines

---

# Core Design Principles

- Transcript data must be serializable
- Structures must support incremental streaming updates
- Timestamps must remain authoritative
- Transcript chunks must support speaker alignment
- API responses should remain frontend-friendly
- Persistence format should closely match API format

---

# 1. Standard Transcript Chunk Structure

Represents finalized transcript segments after:
- Whisper transcription
- diarization alignment
- post-processing

---

## Structure

```json
{
  "speaker": "SPEAKER_00",
  "start": 12.5,
  "end": 15.8,
  "text": "Today we finalized the backend architecture.",
  "confidence": null
}
```

---

## Field Definitions

| Field | Type | Purpose |
|---|---|---|
| speaker | string | assigned speaker label |
| start | float | segment start timestamp |
| end | float | segment end timestamp |
| text | string | transcript content |
| confidence | float / null | optional inference confidence |

Note:
Confidence scores are currently placeholders and may be populated later if segment-level confidence estimation is added to the pipeline.

---

## Purpose

Used for:
- final transcript rendering
- database persistence
- exports
- summaries
- frontend session pages

---

# 2. Incremental Streaming Chunk Structure

Represents partial realtime transcript updates during active microphone streaming.

Unlike finalized transcript chunks:
- these are unstable
- text may evolve over time
- chunks may be overwritten later

---

## Structure

```json
{
  "partial": true,
  "chunk_index": 14,
  "text": "Today we finalized",
  "timestamp": 1716812
}
```

---

## Field Definitions

| Field | Type | Purpose |
|---|---|---|
| partial | boolean | indicates unstable streaming text |
| chunk_index | integer | ordering index |
| text | string | partial transcript |
| timestamp | integer | streaming timestamp |

---

## Why partial=true Exists

Realtime inference produces evolving outputs.

Example:

Initial chunk:

```text
Today we finalized
```

Updated chunk:

```text
Today we finalized the backend architecture
```

Frontend must understand:
- text is still evolving
- chunk may be replaced

---

# 3. Final Session Response Structure

Represents the complete processed session returned to frontend/API consumers.

Supports:
- transcript display
- summaries
- MOM generation
- action item rendering

---

## Structure

```json
{
  "session_id": 1,
  "status": "completed",

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

---

# Field Breakdown

---

## session_id

Unique session identifier.

Used for:
- retrieval APIs
- exports
- frontend routing

---

## status

Processing state.

Possible values:

```text
pending
transcribing
processing
complete
failed
```

---

## transcript

Array of finalized transcript chunks.

Example:

```json
[
  {
    "speaker": "SPEAKER_00",
    "start": 12.5,
    "end": 15.8,
    "text": "Today we finalized the backend architecture."
  }
]
```

---

## summary

Short generated overview of session content.

---

## mom

Structured Minutes of Meeting object.

Contains:
- attendees
- key points
- decisions
- next steps

---

## action_items

Extracted tasks generated from transcript intelligence.

Example:

```json
[
  {
    "task": "Implement upload endpoint",
    "completed": false
  }
]
```

---

# 4. Speaker Mapping Structure

Represents diarization-aligned speaker information.

---

## Structure

```json
{
  "speaker_label": "SPEAKER_00",
  "start": 12.0,
  "end": 15.0
}
```

---

## Purpose

Used for:
- transcript alignment
- frontend speaker visualization
- speaker grouping

---

# 5. Transcript Alignment Strategy

Whisper and pyannote outputs are generated independently.

---

## Whisper Output

Produces:
- text
- timestamps

Example:

```json
{
  "start": 12.3,
  "end": 14.8,
  "text": "Today we finalized the backend architecture."
}
```

---

## pyannote Output

Produces:
- speaker regions

Example:

```json
{
  "speaker": "SPEAKER_00",
  "start": 12.0,
  "end": 15.0
}
```

---

## Alignment Goal

Map:

```text
Whisper transcript
↔
speaker region
```

Result:

```json
{
  "speaker": "SPEAKER_00",
  "start": 12.3,
  "end": 14.8,
  "text": "Today we finalized the backend architecture."
}
```

---

# 6. Streaming Persistence Strategy

Realtime streaming persistence differs from upload processing.

---

## Streaming Flow

```text
Browser audio chunks
→ rolling inference
→ partial transcript generation
→ incremental DB persistence
→ final transcript reconstruction
```

---

## Important Design Rule

Streaming systems are asynchronous.

Therefore:
- insertion order cannot be trusted
- chunk_index must remain authoritative
- timestamps must be preserved

Transcript reconstruction must always use:
- timestamps
- chunk_index ordering

---

# 7. Export Strategy

Finalized transcript structures should support:
- TXT export
- JSON export
- future PDF export
- future DOCX export

Without additional transformation complexity.

---

# 8. Future Improvements

Potential future additions:
- confidence scores
- sentiment metadata
- embeddings
- topic segmentation
- speaker renaming
- transcript search indexing

---

# Final Design Decision

Chunk-based transcript architecture was selected because it supports:
- upload processing
- realtime streaming
- incremental caption updates
- speaker-aware persistence
- frontend rendering
- future scalability
- export compatibility