from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RoomCreated:
    """A host created a room and took the first seat."""

    room_id: str
    host_id: str


@dataclass(frozen=True, slots=True)
class StudentJoined:
    """A student took a seat directly."""

    room_id: str
    student_id: str
    host_id: str


@dataclass(frozen=True, slots=True)
class StudentWaitlisted:
    """A student entered the FIFO queue."""

    room_id: str
    student_id: str
    host_id: str


@dataclass(frozen=True, slots=True)
class StudentLeft:
    """A student gave up a seat or left the queue."""

    room_id: str
    student_id: str


@dataclass(frozen=True, slots=True)
class StudentPromoted:
    """The next student in line received a seat."""

    room_id: str
    student_id: str


@dataclass(frozen=True, slots=True)
class HostChanged:
    """The longest seated remaining member inherited the role."""

    room_id: str
    new_host_id: str


@dataclass(frozen=True, slots=True)
class MemberRemoved:
    """The host removed a seated member."""

    room_id: str
    student_id: str


@dataclass(frozen=True, slots=True)
class RoomClosed:
    """A room became terminal and released its active participants."""

    room_id: str
    recipient_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class MessagePosted:
    """A seated member sent a message."""

    room_id: str
    student_id: str
    message_id: str


@dataclass(frozen=True, slots=True)
class ConnectionRequested:
    """The receiver has a new pending request."""

    request_id: str
    sender_id: str
    receiver_id: str


@dataclass(frozen=True, slots=True)
class ConnectionAccepted:
    """The receiver accepted the request and the link exists."""

    request_id: str
    sender_id: str
    receiver_id: str
