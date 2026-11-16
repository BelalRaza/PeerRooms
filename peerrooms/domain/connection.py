from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType
from typing import ClassVar, Mapping

from peerrooms.domain.enums import RequestStatus
from peerrooms.domain.exceptions import InvalidTransitionError, PermissionDeniedError, ValidationError


@dataclass(eq=False, slots=True)
class ConnectionRequest:
    """A request with an actor-checked transition table (FR10)."""

    id: str
    sender_id: str
    receiver_id: str
    created_at: datetime
    status: RequestStatus = field(default=RequestStatus.PENDING, init=False)
    responded_at: datetime | None = field(default=None, init=False)

    ALLOWED: ClassVar[Mapping[RequestStatus, frozenset[RequestStatus]]] = MappingProxyType({
        RequestStatus.PENDING: frozenset({
            RequestStatus.ACCEPTED, RequestStatus.REJECTED, RequestStatus.CANCELLED,
        }),
        RequestStatus.ACCEPTED: frozenset(),
        RequestStatus.REJECTED: frozenset(),
        RequestStatus.CANCELLED: frozenset(),
    })

    def __post_init__(self) -> None:
        if self.sender_id == self.receiver_id:
            raise ValidationError("You cannot send a connection request to yourself.")

    def accept(self, by_id: str, now: datetime) -> None:
        self._require_receiver(by_id)
        self._move_to(RequestStatus.ACCEPTED, now)

    def reject(self, by_id: str, now: datetime) -> None:
        self._require_receiver(by_id)
        self._move_to(RequestStatus.REJECTED, now)

    def cancel(self, by_id: str, now: datetime) -> None:
        if by_id != self.sender_id:
            raise PermissionDeniedError("Only the sender can cancel this request.")
        self._move_to(RequestStatus.CANCELLED, now)

    def _require_receiver(self, by_id: str) -> None:
        if by_id != self.receiver_id:
            raise PermissionDeniedError("Only the receiver can accept or reject this request.")

    def _move_to(self, target: RequestStatus, now: datetime) -> None:
        if target not in self.ALLOWED[self.status]:
            raise InvalidTransitionError(self.status, target)
        self.status = target
        self.responded_at = now


@dataclass(frozen=True, slots=True)
class Connection:
    """An accepted, unordered link between two individual students (FR11)."""

    id: str
    student_ids: frozenset[str]
    connected_at: datetime

    def __post_init__(self) -> None:
        ids = frozenset(self.student_ids)
        if len(ids) != 2:
            raise ValidationError("A connection must link two distinct students.")
        object.__setattr__(self, "student_ids", ids)

    def other(self, student_id: str) -> str:
        if student_id not in self.student_ids:
            raise ValidationError("The student is not a participant in this connection.")
        return next(iter(self.student_ids - {student_id}))
