from dataclasses import dataclass
from typing import Dict, List


@dataclass
class SummaryPayloadSchema:
    summary: str
    mom: Dict
    action_items: List[str]
