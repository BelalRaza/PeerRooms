from enum import StrEnum


class RoomStatus(StrEnum):
    """Labels for the room lifecycle."""

    OPEN = "OPEN"
    FULL = "FULL"
    CLOSED = "CLOSED"


class RoomRole(StrEnum):
    """A student's role within one room."""

    HOST = "HOST"
    MEMBER = "MEMBER"


class RoomType(StrEnum):
    """Capacity presets supported by the room factory."""

    QUICK_CHAT = "QUICK_CHAT"
    DISCUSSION = "DISCUSSION"
    PANEL = "PANEL"


class RequestStatus(StrEnum):
    """Initial and terminal connection-request states."""

    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class NotificationType(StrEnum):
    """Events that produce an inbox item."""

    STUDENT_JOINED = "STUDENT_JOINED"
    STUDENT_WAITLISTED = "STUDENT_WAITLISTED"
    STUDENT_PROMOTED = "STUDENT_PROMOTED"
    HOST_CHANGED = "HOST_CHANGED"
    MEMBER_REMOVED = "MEMBER_REMOVED"
    ROOM_CLOSED = "ROOM_CLOSED"
    CONNECTION_REQUESTED = "CONNECTION_REQUESTED"
    CONNECTION_ACCEPTED = "CONNECTION_ACCEPTED"


class JoinResult(StrEnum):
    """The two possible successful results of joining."""

    JOINED = "JOINED"
    WAITLISTED = "WAITLISTED"
