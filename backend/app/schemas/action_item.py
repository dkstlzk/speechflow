from dataclasses import dataclass


@dataclass
class ActionItemSchema:
    text: str
    status: str = "open"
