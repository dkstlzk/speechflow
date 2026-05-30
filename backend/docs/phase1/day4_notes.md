# Day 4 — Flask-Native Backend Stabilization & Architecture Finalization

Date:
28/05/2026

Project:
SpeechFlow MVP

Phase:
PHASE 1 — Upload Transcription Pipeline

---

## 1. OVERVIEW

Day 4 expanded beyond initial upload scaffolding because the FastAPI to Flask
migration introduced deeper architectural implications than expected. The
backend needed to be re-centered around Flask-native patterns, SocketIO
threading, and clear service boundaries before any Day 5 AI integration could
begin. This day prioritized infrastructure stabilization, repository cleanup,
and interface readiness so that the actual FFmpeg and Whisper integration would
not be built on unstable or ambiguous architecture.

The decision to stabilize architecture first was deliberate: Whisper,
pyannote, and Ollama processing are heavyweight and long-running, and the
backend needed explicit separation of concerns to avoid mixing inference logic
with request handling. Day 4 therefore became the backbone and execution-flow
finalization milestone for Phase 1.

---

## 2. MAJOR ARCHITECTURE TRANSITION

The backend was migrated fully away from FastAPI assumptions and into a
Flask-native architecture. This involved removing async-first design,
eliminating FastAPI-specific router concepts, and adopting a thread-based
background execution approach for long-running jobs.

Key decisions included:

- API routes are now thin Flask Blueprints (no async routes).
- WebSocket handling is isolated into SocketIO events, not API routes.
- Service-layer orchestration owns business logic.
- Repository layer encapsulates ORM access for persistence.
- Workers own long-running pipeline execution.

This transition was necessary to match the finalized Flask roadmap and to
avoid reintroducing FastAPI assumptions that would complicate the MVP
implementation.

---

## 3. FINALIZED BACKEND ARCHITECTURE

Final backend structure and responsibilities:

- api/: Flask Blueprints, request handling only
- websocket/: SocketIO event handlers only
- services/: business logic and orchestration
- workers/: background pipeline execution
- persistence/: repository access and DB scaffolding
- schemas/: response serialization and API payload shaping
- models/: ORM entities
- db/: SQLAlchemy base and session setup
- config/: environment settings and logging
- docs/: engineering reference documentation
- tests/: lightweight validation and bootstrap checks

The separation ensures that each layer has a single purpose and avoids
mixing route logic with model execution or database persistence.

---

## 4. SERVICES LAYER RESTRUCTURING

Services were refactored into domain-specific subpackages:

- audio/
- transcription/
- diarization/
- summarization/
- persistence/
- session/

Key scaffolds and responsibilities:

- ffmpeg_service.py: define FFmpeg normalization interface
- whisper_service.py: define transcription interfaces for file/stream
- diarization_service.py: define diarization interface
- transcript_service.py: define alignment and transcript orchestration
- summary_service.py: define summary + MOM generation interface
- session_service.py: define session lifecycle helpers
- utils/file_manager.py: temp file helpers, filename sanitization

Generic helper utilities live in app/utils.

All services remain implementation scaffolds. No inference logic was
implemented yet. Day 5 will attach real inference execution to these
interfaces.

---

## 5. WORKER ARCHITECTURE FINALIZATION

Threaded worker scaffolding was added to support background execution:

- upload_pipeline.py: defines pipeline stages and lifecycle transitions
- session_tasks.py: helper methods for marking status changes
- background.py: thread runner utility

The worker flow defines a clear pipeline sequence:

upload -> preprocess -> transcribe -> diarize -> persist -> post-process
-> completion

Flask threading was chosen over async for simplicity and compatibility with
CPU-bound inference. This avoids complex async execution and stays aligned
with MVP constraints.

---

## 6. SESSION STATUS LIFECYCLE

Centralized session lifecycle states were introduced in enums.py:

- pending
- uploaded
- preprocessing
- transcribing
- diarizing
- processing
- completed
- failed

These statuses define the canonical pipeline flow and are reused across
workers, services, and persistence. This prevents inconsistent status naming
and clarifies future session progress tracking.

---

## 7. PERSISTENCE LAYER FINALIZATION

A repository pattern was introduced to keep ORM access separate from business
logic:

- session_repository.py
- transcript_repository.py
- sessions.py
- transcripts.py

This design keeps DB access consistent and prevents API routes from touching
ORM code directly. It also creates a stable foundation for future caching,
batching, or background persistence optimizations.

---

## 8. RESPONSE SCHEMA & SERIALIZATION FLOW

Lightweight Flask-native schemas were defined to avoid Pydantic/FastAPI
assumptions. This includes:

- response.py (ApiResponse + UploadResponseSchema)
- to_dict serialization helpers

The intent is to keep response formatting simple, explicit, and compatible
with plain Flask. This is aligned with MVP simplicity and avoids introducing
unnecessary dependencies.

---

## 9. CONFIGURATION & LOGGING RESTRUCTURING

Configuration and logging were centralized:

- constants.py: defaults and logger namespaces
- logging.py: logger factory and formatting
- settings.py: environment configuration and placeholders

Key configuration coverage:

- upload limits
- allowed extensions
- temp directory
- model placeholders
- structured logging setup

Logger namespaces defined:

- upload
- ffmpeg
- transcription
- diarization
- summarization
- persistence
- websocket
- workers

This ensures consistent logging across the pipeline and avoids ad-hoc logging
statements in implementation code.

---

## 10. TEMP FILE MANAGEMENT STRATEGY

A dedicated file_manager.py module was introduced to manage temp files:

- sanitized filenames
- timestamped temp names
- safe extension checking
- cleanup helper

This is critical for audio processing pipelines where large temp files can
accumulate quickly and must be handled safely.

---

## 11. API RESTRUCTURING

The upload route was redesigned to remain thin and trigger background
processing:

- validates file input
- saves to temp
- creates session metadata
- returns session_id immediately
- kicks off worker thread

No long-running inference is performed in the request handler. This preserves
responsiveness and aligns with Flask-threaded architecture.

---

## 12. MODEL & DATABASE RESTRUCTURING

Models finalized for Phase 1 readiness:

- Session
- TranscriptChunk
- Speaker
- SessionSummary
- ActionItem

Relationships were added for transcript chunks, speakers, summaries, and
action items. Status lifecycle integration was wired using the enum-based
status field. This prepares the persistence layer for diarization and
summarization without introducing heavy logic yet.

---

## 13. DOCUMENTATION CONSOLIDATION

Engineering docs were consolidated into backend/docs:

- architecture.md
- pipeline_flow.md
- database_schema.md
- worker_lifecycle.md
- phase1/day4_notes.md

This ensures implementation references are centralized, maintainable, and
kept close to backend code.

---

## 14. TESTING & VALIDATION

Lightweight pytest coverage was added for bootstrap validation:

- import validation
- app factory bootstrap
- worker stage sanity
- upload route sanity

Final pytest results:

- 5 passed
- 3 skipped
- 2 warnings

Heavy inference tests remain skipped by default via RUN_HEAVY_TESTS to avoid
GPU/CPU expense during Phase 1 scaffolding.

---

## 15. FASTAPI CLEANUP & FINAL VERIFICATION

Final cleanup removed remaining FastAPI dependencies and naming. Regex scans
confirmed no active FastAPI references in code or docs. Historical references
remain only in Phase 0 archives and transition records.

This verification step was critical to ensure the architecture is now
consistently Flask-native.

---

## 16. CURRENT REPOSITORY STATUS

Infrastructure:
DONE

Architecture:
DONE

Worker orchestration:
DONE

Persistence flow:
DONE

Lifecycle management:
DONE

Upload execution flow:
READY

AI inference integration:
NEXT (Day 5)

---

## 17. DAY 5 PREPARATION

Remaining Day 5 work:

- Implement FFmpeg normalization
- WAV conversion pipeline
- faster-whisper integration
- transcript segment extraction
- chunk persistence
- full pipeline execution

Day 4 intentionally stopped before implementing any real inference logic.

---

## 18. FINAL ENGINEERING SUMMARY

Day 4 was the real backend stabilization milestone for SpeechFlow. The project
moved from a reorganized repository into a fully implementation-ready backend
foundation. Flask-native architecture, worker orchestration, persistence
abstraction, and lifecycle management were all finalized before integrating AI
logic.

This ensures that Day 5 can focus purely on inference and pipeline execution
without re-litigating architecture. Day 4 represents the transition from
project setup into true backend engineering readiness.

---

## Related Migration Documentation

Detailed FastAPI -> Flask migration notes, cleanup steps,
dependency restructuring, and transition validation are
documented separately in:

backend/docs/transition_fastapi_to_flask.md

---

Note: No actual FFmpeg, Whisper, or pyannote inference logic was implemented
on Day 4. This was intentional.
