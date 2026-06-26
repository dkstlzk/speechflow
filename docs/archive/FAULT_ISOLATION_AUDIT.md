# SpeechFlow MVP - Fault Isolation Audit

## 1. Fault Isolation Matrix

| Subsystem | Exception Contained? | Worker Survives? | Other Sessions Survive? | Session Recoverable? |
| --------- | -------------------- | ---------------- | ----------------------- | -------------------- |
| **Worker Loop** | YES | YES | YES | YES |
| **Caption Engine** | YES | YES | YES | YES |
| **Transcript Engine** | YES | YES | YES | YES |
| **ThreadPool Tasks** | YES | YES | YES | YES |
| **Session Finalization** | YES | YES | YES | YES |
| **Recovery System** | YES | YES | N/A | YES |

## 2. Failure Scenario Review

### Scenario 1: Exception during boundary detection
* **Status:** ✅ Code Verified
* **What breaks:** The current attempt to slice a segment for transcription is skipped.
* **What survives:** Worker thread and adjacent sessions survive. The next 0.2s tick will retry boundary detection.

### Scenario 2: Exception during Whisper transcription
* **Status:** ✅ Code Verified
* **What breaks:** The transcription text for that specific chunk is lost.
* **What survives:** The `finally:` block strictly executes, setting `is_transcribing = False`. The worker thread survives and continues accepting new audio.

### Scenario 3: Database commit failure
* **Status:** ✅ Code Verified
* **What breaks:** The specific chunk fails to write to PostgreSQL.
* **What survives:** The exception is safely caught inside the `try` block, and the `finally:` block executes, releasing `is_transcribing`. Worker survives.

### Scenario 4: Caption inference failure
* **Status:** ✅ Code Verified
* **What breaks:** That single realtime caption update is skipped.
* **What survives:** The `is_captioning = False` mutex is released either by the outer `except` or the inner `finally`. The worker proceeds seamlessly.

### Scenario 5: Exception during final session teardown
* **Status:** ✅ Code Verified
* **What breaks:** If `handle_session_end` synchronously crashes, the session is not popped from `session_manager.active_sessions`.
* **What survives:** The `try/except` in the worker loop catches the error. The worker thread survives and continues processing other sessions. The background Postgres periodic recovery loop will ensure its database status is eventually corrected.

### Scenario 6: Exception inside recovery loop
* **Status:** ✅ Code Verified
* **What breaks:** That specific 10-minute pass of stale-session database cleanup fails.
* **What survives:** The `except Exception` catch logs the error, the `finally` block closes the database session securely, and the `while True` loop remains active.

---
**Verdict:** PASS (Code-Verified)
The realtime worker architecture possesses an incredibly robust blast-radius containment model. ThreadPool crashes strictly release session mutexes, and database failures do not pollute the event loop.
