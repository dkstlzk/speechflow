from dataclasses import dataclass
from typing import Optional


@dataclass
class TranscriptChunkSchema:
    speaker: str
    start: float
    end: float
    text: str
    confidence: Optional[float] = None
