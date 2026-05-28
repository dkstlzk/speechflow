from dataclasses import asdict, dataclass
from typing import Optional


@dataclass
class TranscriptChunkSchema:
    speaker: str
    start: float
    end: float
    text: str
    confidence: Optional[float] = None

    def to_dict(self) -> dict:
        return asdict(self)
