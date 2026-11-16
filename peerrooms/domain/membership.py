from dataclasses import dataclass
from datetime import datetime

from peerrooms.domain.enums import RoomRole


@dataclass(frozen=True, slots=True)
class Membership:
    """The association between a seated student and a room (FR5, FR6)."""

    student_id: str
    role: RoomRole
    joined_at: datetime
