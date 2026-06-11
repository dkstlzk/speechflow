# SpeechFlow Cleanup Audit

| Issue | Status | Risk | Recommended Action |
| ----- | ------ | ---- | ------------------ |
| 1. Unbound DB Variable | Confirmed | Medium | Initialize `db = None` before `try` block |
| 2. Test Suite Breakage | Confirmed | Medium | Inject `SECRET_KEY` inside `conftest.py` |
| 3. Duplicate Logging Import | Confirmed | Low | Remove redundant import |
| 4. Duplicate Migration Log | Confirmed | Low | Remove redundant logger statement |
| 5. Finalize Busy-Wait | Confirmed | Low | Option A: Keep current behavior |
| 6. Remaining Settings() | Invalid | None | No action required |
| 7. Dead Code Verification | Confirmed | Low | Remove streaming/whisper stubs; retain ollama |
| 8. Root-Level Debug Scripts | Confirmed | Low | Move to `scripts/debug/` folder |

---

## Issue 1 — Unbound DB Variable
**Status**: Confirmed
- **File**: `backend/app/main.py`
- **Lines**: 66-78
- **Finding**: Inside the `__main__` block, `from .db.session import SessionLocal` and `db = SessionLocal()` are executed inside the `try` block. If the import or initialization raises an exception, the execution jumps to `finally: db.close()`, which will raise a `NameError` because `db` is globally unbound.
- **Impact**: Masks the original exception causing the crash with a confusing `NameError`.
- **Implementation Plan**: Move `db = None` before the `try` block, and change the finally block to `if db is not None: db.close()`.

## Issue 2 — Test Suite Breakage From SECRET_KEY
**Status**: Confirmed
- **Files**: `backend/app/config/settings.py` (Line 18), `backend/tests/conftest.py`
- **Finding**: `Settings.__post_init__()` strictly checks for `SECRET_KEY`. When `conftest.py` imports `create_app`, the module cascade now instantiates the `settings` singleton immediately. Because `conftest.py` does not mock `SECRET_KEY`, the test suite immediately crashes with `RuntimeError` before running a single test.
- **Impact**: Breaks automated CI and local test runs.
- **Implementation Plan**: Add `os.environ.setdefault("SECRET_KEY", "test-only-key")` alongside the existing database stubs in `conftest.py` before `create_app` is imported.

## Issue 3 — Duplicate Logging Import
**Status**: Confirmed
- **File**: `backend/app/main.py`
- **Lines**: 11 and 21
- **Finding**: `from .config.logging import configure_logging` is imported on line 11. On line 21, it is imported again alongside `get_logger`. 
- **Impact**: Zero runtime impact (Python caches modules), but it clutters the file.
- **Implementation Plan**: Remove the duplicate `configure_logging` import from line 21.

## Issue 4 — Duplicate Migration Log
**Status**: Confirmed
- **File**: `backend/app/db/migrations.py`
- **Lines**: 65 and 67
- **Finding**: `logger.info("Added 'audio_path' column to sessions table")` is repeated consecutively.
- **Impact**: Pollutes the stdout logs during startup with duplicate messages.
- **Implementation Plan**: Delete the repeated log statement.

## Issue 5 — Finalize Busy-Wait
**Status**: Confirmed
- **File**: `backend/app/api/realtime.py`
- **Lines**: 64-73
- **Finding**: The `/finalize` endpoint runs a polling loop `time.sleep(0.1)` up to 50 times (5 seconds) waiting for `session_manager` to destroy the session. 
- **Impact**: It technically blocks a single Werkzeug request thread. However, since the WebSockets run asynchronously via Eventlet threads, the background transcription job safely completes and emits the event. 
- **Recommendation**: **Option A (Keep current behavior)**. Returning a 202 Async (Option C) would require rewriting the frontend to disconnect and rely solely on socket events instead of the HTTP success response. For this stage, a maximum 5-second wait on an HTTP request thread is completely acceptable.

## Issue 6 — Remaining Settings() Instantiations
**Status**: Invalid / Already Fixed
- **Finding**: A rigorous repository sweep confirms that the string `Settings()` only appears once across the entire `backend/app` directory—inside `config/settings.py` itself to instantiate the singleton. 
- **Implementation Plan**: No action required. The codebase is fully decoupled.

## Issue 7 — Dead Code Verification
**Status**: Confirmed (Partially)
- **A. `streaming.py -> get_current_segment_duration()`**: Confirmed unused.
- **B. `whisper_service.py -> transcribe_stream_window()`**: Confirmed unused.
- **C. `ollama.py -> summarize_transcript()`**: Unused outside of `__init__.py`.
- **Implementation Plan**: 
  - Delete `get_current_segment_duration` and `transcribe_stream_window` completely. 
  - **Keep** `summarize_transcript()` as a future scaffold, as Phase 4 intelligence integration is the next roadmap item.

## Issue 8 — Root-Level Debug Scripts
**Status**: Confirmed
- **Files**: `check_enum.py`, `test_fts_rollback.py`, `test_pause_bug.py`, `test_pause_privacy.py`
- **Finding**: These manual diagnostic scripts are sitting in the root of the project. They are not hooked into `pytest` or any CI pipeline.
- **Impact**: Clutters the root directory.
- **Implementation Plan**: Do not delete them, as they are valuable for forensic testing. Instead, create a `scripts/debug/` directory and move them there.
