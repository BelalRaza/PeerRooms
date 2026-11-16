from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Message:
    """A chat line owned by a room (FR7)."""

    id: str
    room_id: str
    sender_id: str
    content: str
    sent_at: datetime
