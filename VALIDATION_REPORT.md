# SpeechFlow Validation Report

This document records the final end-to-end testing results for the SpeechFlow MVP. It serves as evidence of system stability, functional correctness, and resilience under realistic production conditions.

## 1. Functional Validation

| Test Scenario | Result | Notes |
| :--- | :--- | :--- |
| **Upload: 1 min audio** | ⬜ Pending | |
| **Upload: 10 min audio** | ⬜ Pending | |
| **Upload: 40–60 min audio** | ⬜ Pending | |
| **Upload: Hindi Language** | ⬜ Pending | |
| **Upload: Hinglish (Mixed)** | ⬜ Pending | |
| **Upload: Multiple Speakers** | ⬜ Pending | |
| **Upload: Single Speaker** | ⬜ Pending | |
| **Verify: Summary Generation** | ⬜ Pending | |
| **Verify: MoM Generation** | ⬜ Pending | |
| **Verify: Action Items** | ⬜ Pending | |
| **Verify: Export (DOCX/TXT/PDF)**| ⬜ Pending | |
| **Verify: Search Functionality** | ⬜ Pending | |
| **Realtime: 2 Speakers** | ⬜ Pending | |
| **Realtime: 3 Speakers** | ⬜ Pending | |
| **Realtime: Silence Handling** | ⬜ Pending | |
| **Realtime: Interruptions** | ⬜ Pending | |
| **Realtime: Long Recording** | ⬜ Pending | |
| **Translation: EN → HI** | ⬜ Pending | |
| **Translation: HI → EN** | ⬜ Pending | |
| **Translation: Hinglish Base** | ⬜ Pending | |

## 2. Failure Injection & Resilience

| Test Scenario | Result | Notes |
| :--- | :--- | :--- |
| **Upload Crash Recovery**<br>*(Kill backend mid-upload, restart)* | ⬜ Pending | Expecting session to cleanly fail or recover without hanging forever. |
| **Realtime Network Drop**<br>*(Disconnect WiFi, reconnect)* | ⬜ Pending | Expecting socket reconnect, surviving transcript, and successful finalization. |
| **Realtime Crash Recovery**<br>*(Kill backend mid-recording)* | ⬜ Pending | Expecting stranded `.raw` audio to be rescued and converted to `.wav` on restart. |
| **Ollama Outage**<br>*(Kill Ollama during transcription)* | ⬜ Pending | Expecting safe fallback to `FAILED` state and retry capability. |
| **Translation Worker Crash**<br>*(Kill translation worker)* | ⬜ Pending | Expecting translation row to accurately reflect `failed` state and allow retry. |

## 3. Concurrency Safety

| Test Scenario | Result | Notes |
| :--- | :--- | :--- |
| **Concurrent `/process`**<br>*(Trigger multiple process requests)* | ⬜ Pending | Expecting 1 success, others receive `409 Conflict`. No duplicate intelligence workers. |
| **Concurrent `/translate`**<br>*(Spam translate button)* | ⬜ Pending | Expecting only one translation row per language to be spawned. |
| **Concurrent `/diarize`**<br>*(Spam diarize button)* | ⬜ Pending | Expecting `409 Conflict` for overlapping requests. |

## 4. Performance Benchmarks

| Component | Target Baseline (30m meeting) | Actual Measured Time | Notes / Bottleneck Assessment |
| :--- | :--- | :--- | :--- |
| **Preprocessing** | < 10s | ⬜ Pending | |
| **Whisper Transcription** | < 20m | ⬜ Pending | |
| **Pyannote Diarization** | ~ 45m | ⬜ Pending | Expected to be the primary bottleneck. |
| **Text Alignment** | < 1m | ⬜ Pending | |
| **Intelligence (Ollama)** | < 3m | ⬜ Pending | |
| **Translation** | < 1m | ⬜ Pending | |

## 5. Deployment Verification

| Test Scenario | Result | Notes |
| :--- | :--- | :--- |
| **Clean Database Init** | ⬜ Pending | |
| **Clean Model Download** | ⬜ Pending | HuggingFace cache and Ollama pulls successful. |
| **Frontend Boot** | ⬜ Pending | UI accessible on port 80. |
| **End-to-End Success** | ⬜ Pending | Upload, process, and export works without manual intervention. |
