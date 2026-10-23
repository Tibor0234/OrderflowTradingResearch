from dataclasses import dataclass

@dataclass(slots=True)
class NewsMessage:
    external_id: int
    time: int
    category: str
    headline: str
    summary: str