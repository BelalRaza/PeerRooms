from peerrooms.domain.enums import RequestStatus


class PeerRoomsError(Exception):
    """Root of the business-rule error hierarchy."""


class ValidationError(PeerRoomsError):
    """An input does not meet a domain rule."""


class NotFoundError(PeerRoomsError):
    """The requested entity does not exist."""


class PermissionDeniedError(PeerRoomsError):
    """The acting student lacks permission for this operation."""


class ConflictError(PeerRoomsError):
    """The requested action conflicts with existing data."""


class RoomError(ConflictError):
    """An action conflicts with the state of a room."""


class InvalidCapacityError(ValidationError):
    """The capacity falls outside the room type's range."""


class DuplicateEmailError(ConflictError):
    """The email address is already registered."""


class AlreadyInRoomError(RoomError):
    """The student is already seated or on the waitlist."""

    def __init__(self, student_id: str, room_id: str) -> None:
        super().__init__(f"Student {student_id} is already seated or waitlisted in room {room_id}.")


class RoomClosedError(RoomError):
    """The operation requires an active room."""

    def __init__(self, room_id: str) -> None:
        super().__init__(f"Room {room_id} is closed.")


class NotAMemberError(RoomError):
    """The operation requires a seat or a spot on the waitlist."""


class StudentNotFoundError(NotFoundError):
    """The student ID or email address is unknown."""


class RoomNotFoundError(NotFoundError):
    """The room ID is unknown."""


class RequestNotFoundError(NotFoundError):
    """The connection-request ID is unknown."""


class NotificationNotFoundError(NotFoundError):
    """The notification ID is unknown."""


class AlreadyConnectedError(ConflictError):
    """The pair already shares a connection."""


class DuplicateRequestError(ConflictError):
    """A request is already pending between the same pair."""


class InvalidTransitionError(ConflictError):
    """The request has already reached a terminal state."""

    def __init__(self, current: RequestStatus, target: RequestStatus) -> None:
        super().__init__(f"Cannot change a {current.value} request to {target.value}.")


class BlockedError(PermissionDeniedError):
    """A student in the pair has blocked the other."""
