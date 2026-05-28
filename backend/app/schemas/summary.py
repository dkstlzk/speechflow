from dataclasses import asdict, dataclass
from typing import Dict, List


@dataclass
class SummaryPayloadSchema:
    summary: str
    mom: Dict
    action_items: List[str]

    def to_dict(self) -> dict:
        return asdict(self)
