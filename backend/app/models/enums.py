from enum import Enum


class SessionStatus(str, Enum):
    PENDING = "pending"
    UPLOADED = "uploaded"
    PREPROCESSING = "preprocessing"
    TRANSCRIBING = "transcribing"
    DIARIZING = "diarizing"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


SESSION_STATUS_FLOW = [
    SessionStatus.PENDING,
    SessionStatus.UPLOADED,
    SessionStatus.PREPROCESSING,
    SessionStatus.TRANSCRIBING,
    SessionStatus.DIARIZING,
    SessionStatus.PROCESSING,
    SessionStatus.COMPLETED,
]
