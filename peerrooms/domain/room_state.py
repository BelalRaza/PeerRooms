from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from peerrooms.domain.enums import JoinResult, RoomRole, RoomStatus
from peerrooms.domain.exceptions import RoomClosedError

if TYPE_CHECKING:
    from peerrooms.domain.room import Room


@dataclass(frozen=True, slots=True)
class JoinOutcome:
    """A seat or a one-based waitlist position."""

    result: JoinResult
    position: int | None = None


@dataclass(frozen=True, slots=True)
class LeaveResult:
    """The side effects of releasing a seat or leaving the waitlist."""

    promoted_id: str | None = None
    new_host_id: str | None = None
    closed: bool = False


class RoomState(ABC):
    """The State interface for operations whose behavior depends on occupancy."""

    @abstractmethod
    def join(self, room: Room, student_id: str, now: datetime) -> JoinOutcome: ...

    @abstractmethod
    def leave(self, room: Room, student_id: str, now: datetime) -> LeaveResult: ...

    @abstractmethod
    def close(self, room: Room) -> None: ...

    @abstractmethod
    def status(self) -> RoomStatus: ...

    def require_active(self, room: Room) -> None:
        """Guard operations that cannot run on a closed room."""


class OpenState(RoomState):
    """Seat new participants directly while there is capacity."""

    def join(self, room: Room, student_id: str, now: datetime) -> JoinOutcome:
        room._seat(student_id, RoomRole.MEMBER, now)
        if room.is_full():
            room._set_state(FullState())
        return JoinOutcome(JoinResult.JOINED)

    def leave(self, room: Room, student_id: str, now: datetime) -> LeaveResult:
        leaving = room._unseat(student_id)
        if not room.members:
            self.close(room)
            return LeaveResult(closed=True)
        new_host = room._transfer_host() if leaving.role is RoomRole.HOST else None
        return LeaveResult(new_host_id=new_host)

    def close(self, room: Room) -> None:
        _close(room)

    def status(self) -> RoomStatus:
        return RoomStatus.OPEN


class FullState(RoomState):
    """Queue new arrivals and promote the next student when a seat opens."""

    def join(self, room: Room, student_id: str, now: datetime) -> JoinOutcome:
        room._waitlist.append(student_id)
        return JoinOutcome(JoinResult.WAITLISTED, len(room._waitlist))

    def leave(self, room: Room, student_id: str, now: datetime) -> LeaveResult:
        leaving = room._unseat(student_id)
        promoted = room._promote_next(now)
        if promoted is None:
            room._set_state(OpenState())
        new_host = room._transfer_host() if leaving.role is RoomRole.HOST else None
        return LeaveResult(promoted_id=promoted, new_host_id=new_host)

    def close(self, room: Room) -> None:
        _close(room)

    def status(self) -> RoomStatus:
        return RoomStatus.FULL


class ClosedState(RoomState):
    """Reject mutations in the terminal room state."""

    def join(self, room: Room, student_id: str, now: datetime) -> JoinOutcome:
        raise RoomClosedError(room.id)

    def leave(self, room: Room, student_id: str, now: datetime) -> LeaveResult:
        raise RoomClosedError(room.id)

    def close(self, room: Room) -> None:
        raise RoomClosedError(room.id)

    def status(self) -> RoomStatus:
        return RoomStatus.CLOSED

    def require_active(self, room: Room) -> None:
        raise RoomClosedError(room.id)



def _close(room: Room) -> None:
    room._members.clear()
    room._waitlist.clear()
    room.host_id = None
    room._set_state(ClosedState())
