from enum import Enum


class SessionStatus(str, Enum):
    # Upload pipeline states
    PENDING = "pending"
    UPLOADED = "uploaded"
    PREPROCESSING = "preprocessing"
    TRANSCRIBING = "transcribing"
    DIARIZING = "diarizing"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    # Realtime pipeline states
    RECORDING = "recording"
    FINALIZING = "finalizing"
    REVIEW = "review"
    SAVED = "saved"


SESSION_STATUS_FLOW = [
    SessionStatus.PENDING,
    SessionStatus.UPLOADED,
    SessionStatus.PREPROCESSING,
    SessionStatus.TRANSCRIBING,
    SessionStatus.DIARIZING,
    SessionStatus.PROCESSING,
    SessionStatus.COMPLETED,
]

REALTIME_STATUS_FLOW = [
    SessionStatus.RECORDING,
    SessionStatus.FINALIZING,
    SessionStatus.REVIEW,
    SessionStatus.SAVED,
]
