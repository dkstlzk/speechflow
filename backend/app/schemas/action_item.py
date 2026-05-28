from dataclasses import asdict, dataclass


@dataclass
class ActionItemSchema:
    text: str
    status: str = "open"

    def to_dict(self) -> dict:
        return asdict(self)
