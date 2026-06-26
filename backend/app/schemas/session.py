from dataclasses import asdict, dataclass
from typing import List, Optional

from .transcript import TranscriptChunkSchema


@dataclass
class SessionResponseSchema:
    session_id: int
    status: str
    transcript: List[TranscriptChunkSchema]
    summary: str = ""
    mom: Optional[dict] = None
    action_items: Optional[list] = None
    title: Optional[str] = None
    host_name: Optional[str] = None
    participants: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)
