# FastAPI to Flask Transition Report

Date: 28/05/2026

## Purpose

This document captures the complete FastAPI to Flask transition performed in
this repo, including restructuring, documentation consolidation, environment
finalization, tests executed, and final status.

## High-Level Summary

The backend was migrated from a FastAPI-centric layout to a Flask +
Flask-SocketIO architecture while preserving the MVP scope (upload + realtime
streaming + transcript intelligence). The repo now has a clean Flask-native
structure, consolidated engineering docs, Phase 0 archival, and a stable
Python environment with pytest-compatible smoke checks.

## Major Structural Changes

- Replaced FastAPI entrypoint with a Flask app factory and SocketIO bootstrap.
- Replaced routers/ with api/ (Flask Blueprints).
- Separated websocket handling into websocket/events.py.
- Split services by domain: audio, transcription, diarization, summarization,
  persistence.
- Added workers/background.py for thread-based execution.
- Added config/settings.py for environment-driven configuration.
- Added SQLAlchemy base/session and ORM models for persistence.
- Consolidated docs under backend/docs, with Phase 0 archived.

## New Backend Layout (Key Paths)

- backend/app/main.py: Flask app factory + SocketIO init
- backend/app/api/: upload, sessions, actions
- backend/app/websocket/events.py: realtime event handlers
- backend/app/services/: audio, transcription, diarization, summarization,
  persistence
- backend/app/models/: Session, TranscriptChunk, Speaker, Summary, ActionItem
- backend/app/db/: Base and SessionLocal
- backend/app/workers/background.py: thread helper

## Documentation Changes

- Consolidated detailed engineering docs into:
  - backend/docs/architecture.md
  - backend/docs/pipeline_flow.md
  - backend/docs/database_schema.md
- Archived Phase 0 reference docs to backend/docs/archive/phase0.
- README updated to reflect Flask-native architecture and new docs location.

## Environment and Dependency Changes

- Split requirements into:
  - backend/requirements/base.txt
  - backend/requirements/dev.txt
- Installed dependencies in the venv.
- Created a frozen snapshot at backend/requirements/lock.txt.
- Removed leftover FastAPI from the environment and re-froze the lock file.

## Tests and Validation Performed

1. Pytest import validation converted to real tests and executed:
   - backend/tests/test_imports.py

2. Flask app factory smoke test added and executed:
   - backend/tests/test_app_bootstrap.py

3. Upload route and worker bootstrap checks added:
   - backend/tests/test_upload_route.py
   - backend/tests/test_worker_bootstrap.py

4. Phase 1 pipeline scaffolding validation added:
   - backend/tests/test_ffmpeg_service.py
   - backend/tests/test_transcription_service.py
   - backend/tests/test_persistence_flow.py
   - backend/tests/test_worker_execution.py

5. Heavy model tests made opt-in using RUN_HEAVY_TESTS:
   - backend/tests/test_whisper.py
   - backend/tests/test_diarization.py
   - backend/tests/test_pyannote.py

6. Final pytest run:
   - 13 passed, 3 skipped, 0 failures

7. Final FastAPI wording scan:
   - No FastAPI references in active code/docs/README/requirements
   - Only Phase 0 archives retain historical FastAPI mentions

## Terminal Commands Executed (Key Steps)

- Moved Phase 0 docs into archives and consolidated docs
- Removed old FastAPI router and placeholder files
- Installed dependencies in venv
- Ran pytest and import checks
- Removed fastapi and regenerated lock file

Examples of key commands:

- python -m pytest
- python backend/tests/test_imports.py
- pip freeze > backend/requirements/lock.txt
- pip uninstall fastapi

## Known Warnings (Non-blocking)

- opentelemetry importlib metadata deprecation warning
- pydub audioop deprecation warning

These do not affect Phase 0 closure.

## Final Status

- FastAPI fully removed from active backend
- Flask + Flask-SocketIO architecture stabilized
- Docs consolidated and Phase 0 archived
- Environment finalized and reproducible
- Pytest passes cleanly with lightweight smoke checks

## Next Steps (Phase 1)

- Implement upload pipeline: FFmpeg -> Whisper -> diarization -> persistence
- Wire session lifecycle updates and transcript chunk persistence
- Add summarization prompts and Ollama integration
- Implement streaming pipeline with rolling buffer and VAD gating
