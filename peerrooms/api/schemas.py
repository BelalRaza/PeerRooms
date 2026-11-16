from datetime import datetime

from pydantic import BaseModel, ConfigDict, StrictInt, StrictStr

from peerrooms.domain.enums import JoinResult, NotificationType, RequestStatus, RoomRole, RoomStatus, RoomType


class RequestModel(BaseModel):
    """The base contract for JSON input."""

    model_config = ConfigDict(extra="forbid")


class InterestsRequest(RequestModel):
    """A replacement list of raw interests."""

    interests: list[StrictStr]


class RegisterRequest(InterestsRequest):
    """Profile values for a new student."""

    name: StrictStr
    email: StrictStr
    department: StrictStr
    year: StrictInt


class SignInRequest(RequestModel):
    """An email-only sign-in for the demo."""

    email: StrictStr


class CreateRoomRequest(RequestModel):
    """Metadata and optional custom capacity for a new room."""

    topic: StrictStr
    prompt: StrictStr
    tags: list[StrictStr]
    room_type: RoomType
    capacity: StrictInt | None = None


class PostMessageRequest(RequestModel):
    """A chat message written by a seated student."""

    content: StrictStr


class SendConnectionRequest(RequestModel):
    """The recipient of a new connection request."""

    receiver_id: StrictStr


class ResponseModel(BaseModel):
    """Serialize the facade's transport-independent views."""

    model_config = ConfigDict(from_attributes=True)


class StudentResponse(ResponseModel):
    """A normalized, signed-in or discoverable student profile."""

    id: str
    name: str
    email: str
    department: str
    year: int
    interests: list[str]


class RoomCardResponse(ResponseModel):
    """Room status, capacity, and the current viewer's position."""

    id: str
    topic: str
    tags: list[str]
    room_type: RoomType
    status: RoomStatus
    capacity: int
    seated_count: int
    created_at: datetime
    viewer_role: RoomRole | None
    viewer_waitlist_position: int | None


class MemberResponse(ResponseModel):
    """The identity and role of a seated member."""

    student_id: str
    name: str
    role: RoomRole
    joined_at: datetime


class WaitlistPositionResponse(ResponseModel):
    """A queue position that preserves other students' privacy."""

    position: int
    is_you: bool


class MessageResponse(ResponseModel):
    """An authored room message."""

    id: str
    room_id: str
    sender_id: str
    sender_name: str
    content: str
    sent_at: datetime


class RoomDetailResponse(RoomCardResponse):
    """A room's prompt, active participants, and recent chat."""

    prompt: str
    members: list[MemberResponse]
    waitlist: list[WaitlistPositionResponse]
    messages: list[MessageResponse]


class JoinResponse(ResponseModel):
    """A seat or a one-based queue position."""

    result: JoinResult
    position: int | None


class LeaveResponse(ResponseModel):
    """Changes caused by the viewer leaving the room."""

    promoted_id: str | None
    new_host_id: str | None
    closed: bool


class PeerResponse(ResponseModel):
    """A suggested student and their matching evidence."""

    student: StudentResponse
    score: float
    common_interests: list[str]


class ConnectionRequestResponse(ResponseModel):
    """A connection request viewed by one of its participants."""

    id: str
    sender_id: str
    sender_name: str
    receiver_id: str
    receiver_name: str
    status: RequestStatus
    created_at: datetime
    responded_at: datetime | None


class PendingRequestsResponse(ResponseModel):
    """Open connection requests grouped by direction."""

    incoming: list[ConnectionRequestResponse]
    outgoing: list[ConnectionRequestResponse]


class ConnectionResponse(ResponseModel):
    """A new connection created by accepting a request."""

    id: str
    student: StudentResponse
    connected_at: datetime


class NotificationResponse(ResponseModel):
    """A single item in the signed-in student's inbox."""

    id: str
    type: NotificationType
    text: str
    is_read: bool
    created_at: datetime
