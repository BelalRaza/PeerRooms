from dataclasses import dataclass
from datetime import datetime

from peerrooms.domain.enums import NotificationType


@dataclass(eq=False, slots=True)
class Notification:
    """An inbox item owned by one student (FR12)."""

    id: str
    recipient_id: str
    type: NotificationType
    text: str
    created_at: datetime
    is_read: bool = False

    def mark_read(self) -> None:
        self.is_read = True
