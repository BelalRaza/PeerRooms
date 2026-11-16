from dataclasses import dataclass
from datetime import datetime

from peerrooms.domain.enums import JoinResult, NotificationType, RequestStatus, RoomRole, RoomStatus, RoomType
from peerrooms.domain.interest import Interest
from peerrooms.domain.room import Room
from peerrooms.domain.student import Student


@dataclass(frozen=True, slots=True)
class StudentView:
    """A student's public profile fields, with interests ready for display."""

    id: str
    name: str
    email: str
    department: str
    year: int
    interests: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RoomCardView:
    """Room metadata and the viewer's seating or queue status."""

    id: str
    topic: str
    tags: tuple[str, ...]
    room_type: RoomType
    status: RoomStatus
    capacity: int
    seated_count: int
    created_at: datetime
    viewer_role: RoomRole | None
    viewer_waitlist_position: int | None


@dataclass(frozen=True, slots=True)
class MemberView:
    """A seated participant and their role in the room."""

    student_id: str
    name: str
    role: RoomRole
    joined_at: datetime


@dataclass(frozen=True, slots=True)
class WaitlistPositionView:
    """A queue position with the viewer's own entry identified."""

    position: int
    is_you: bool


@dataclass(frozen=True, slots=True)
class MessageView:
    """A display-ready room message."""

    id: str
    room_id: str
    sender_id: str
    sender_name: str
    content: str
    sent_at: datetime


@dataclass(frozen=True, slots=True)
class RoomDetailView(RoomCardView):
    """A room card plus its prompt, active participants, and recent messages."""

    prompt: str
    members: tuple[MemberView, ...]
    waitlist: tuple[WaitlistPositionView, ...]
    messages: tuple[MessageView, ...]


@dataclass(frozen=True, slots=True)
class JoinView:
    """The outcome of joining and, if queued, the position."""

    result: JoinResult
    position: int | None


@dataclass(frozen=True, slots=True)
class LeaveView:
    """The observable outcomes of leaving a room."""

    promoted_id: str | None
    new_host_id: str | None
    closed: bool


@dataclass(frozen=True, slots=True)
class PeerView:
    """A candidate, similarity score, and matching tags."""

    student: StudentView
    score: float
    common_interests: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RequestView:
    """The participants, history, and status of a request."""

    id: str
    sender_id: str
    sender_name: str
    receiver_id: str
    receiver_name: str
    status: RequestStatus
    created_at: datetime
    responded_at: datetime | None


@dataclass(frozen=True, slots=True)
class PendingRequestsView:
    """Pending requests grouped by the viewer's role."""

    incoming: tuple[RequestView, ...]
    outgoing: tuple[RequestView, ...]


@dataclass(frozen=True, slots=True)
class ConnectionView:
    """The other student in a newly accepted connection."""

    id: str
    student: StudentView
    connected_at: datetime


@dataclass(frozen=True, slots=True)
class NotificationView:
    """One inbox entry for a signed-in student."""

    id: str
    type: NotificationType
    text: str
    is_read: bool
    created_at: datetime


def interest_names(interests: frozenset[Interest]) -> tuple[str, ...]:
    return tuple(sorted(interest.name for interest in interests))


def student_view(student: Student) -> StudentView:
    return StudentView(
        student.id, student.name, student.email, student.department, student.year,
        interest_names(student.interests),
    )


def room_card(room: Room, viewer_id: str) -> RoomCardView:
    role = next((member.role for member in room.members if member.student_id == viewer_id), None)
    position = next((n for n, waiting in enumerate(room.waitlist, 1) if waiting == viewer_id), None)
    return RoomCardView(
        room.id, room.topic, interest_names(room.tags), room.room_type, room.status(),
        room.capacity, len(room.members), room.created_at, role, position,
    )
