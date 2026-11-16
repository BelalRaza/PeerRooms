from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field, replace
from datetime import datetime
from uuid import uuid4

from peerrooms.domain.enums import RoomRole, RoomStatus, RoomType
from peerrooms.domain.exceptions import (
    AlreadyInRoomError, NotAMemberError, PermissionDeniedError, ValidationError,
)
from peerrooms.domain.interest import Interest
from peerrooms.domain.membership import Membership
from peerrooms.domain.message import Message
from peerrooms.domain.room_state import (
    ClosedState, FullState, JoinOutcome, LeaveResult, OpenState, RoomState,
)


@dataclass(eq=False, slots=True)
class Room:
    """Aggregate root that guards seating, moderation, and messages (State, FR3–FR8)."""

    id: str
    topic: str
    prompt: str
    tags: frozenset[Interest]
    room_type: RoomType
    capacity: int
    host_id: str | None
    created_at: datetime
    _state: RoomState = field(init=False, default_factory=OpenState, repr=False)
    _members: list[Membership] = field(init=False, default_factory=list, repr=False)
    _waitlist: deque[str] = field(init=False, default_factory=deque, repr=False)
    _past_participants: set[str] = field(init=False, default_factory=set, repr=False)
    _messages: list[Message] = field(init=False, default_factory=list, repr=False)

    def __post_init__(self) -> None:
        self.topic, self.prompt = self.topic.strip(), self.prompt.strip()
        self.tags = frozenset(self.tags)
        if not (self.topic and self.prompt and self.tags and self.host_id):
            raise ValidationError("A room needs a topic, prompt, at least one tag, and a host.")
        if type(self.capacity) is not int or self.capacity < 2:
            raise ValidationError("A room needs capacity for at least two students.")
        self._seat(self.host_id, RoomRole.HOST, self.created_at)
        self._check_invariants()

    @property
    def members(self) -> tuple[Membership, ...]:
        return tuple(self._members)

    @property
    def waitlist(self) -> tuple[str, ...]:
        return tuple(self._waitlist)

    @property
    def past_participants(self) -> frozenset[str]:
        return frozenset(self._past_participants)

    @property
    def messages(self) -> tuple[Message, ...]:
        return tuple(self._messages)

    def is_member(self, student_id: str) -> bool:
        return any(member.student_id == student_id for member in self._members)

    def is_full(self) -> bool:
        return len(self._members) == self.capacity

    def status(self) -> RoomStatus:
        return self._state.status()

    def join(self, student_id: str, now: datetime) -> JoinOutcome:
        if self.is_member(student_id) or student_id in self._waitlist:
            raise AlreadyInRoomError(student_id, self.id)
        result = self._state.join(self, student_id, now)
        self._check_invariants()
        return result

    def leave(self, student_id: str, now: datetime) -> LeaveResult:
        if student_id in self._waitlist:
            self._waitlist.remove(student_id)
            result = LeaveResult()
        else:
            result = self._state.leave(self, student_id, now)
        self._check_invariants()
        return result

    def remove_member(self, by_id: str, target_id: str, now: datetime) -> LeaveResult:
        self._require_host(by_id)
        if target_id == by_id:
            raise ValidationError("The host should leave the room instead of removing themselves.")
        if not self.is_member(target_id):
            raise NotAMemberError("Only a seated member can be removed.")
        return self.leave(target_id, now)

    def post_message(self, sender_id: str, content: str, now: datetime) -> Message:
        self._state.require_active(self)
        if not self.is_member(sender_id):
            raise NotAMemberError("Only seated members can post messages.")
        if not content.strip() or len(content) > 1000:
            raise ValidationError("A message must contain between 1 and 1000 characters.")
        message = Message(uuid4().hex, self.id, sender_id, content.strip(), now)
        self._messages.append(message)
        self._check_invariants()
        return message

    def close(self, by_id: str) -> None:
        if self.host_id is not None:
            self._require_host(by_id)
        self._state.close(self)
        self._check_invariants()

    def _require_host(self, student_id: str) -> None:
        self._state.require_active(self)
        if self.host_id != student_id:
            raise PermissionDeniedError("Only the current host can moderate this room.")

    def _seat(self, student_id: str, role: RoomRole, now: datetime) -> None:
        self._members.append(Membership(student_id, role, now))
        self._past_participants.add(student_id)

    def _unseat(self, student_id: str) -> Membership:
        for index, member in enumerate(self._members):
            if member.student_id == student_id:
                return self._members.pop(index)
        raise NotAMemberError(f"The student does not have a seat in room {self.id}.")

    def _set_state(self, state: RoomState) -> None:
        self._state = state

    def _promote_next(self, now: datetime) -> str | None:
        if self._waitlist:
            student_id = self._waitlist.popleft()
            self._seat(student_id, RoomRole.MEMBER, now)
            return student_id
        return None

    def _transfer_host(self) -> str:
        index = min(range(len(self._members)), key=lambda i: self._members[i].joined_at)
        member = replace(self._members[index], role=RoomRole.HOST)
        self._members[index] = member
        self.host_id = member.student_id
        return member.student_id

    def _check_invariants(self) -> None:
        seated = {member.student_id for member in self._members}
        hosts = [member.student_id for member in self._members if member.role is RoomRole.HOST]
        assert len(seated) == len(self._members) <= self.capacity
        assert len(self._waitlist) == len(set(self._waitlist))
        assert seated.isdisjoint(self._waitlist)
        assert seated <= self._past_participants
        assert hosts == ([self.host_id] if seated else [])
        assert bool(self.host_id) == bool(seated)
        assert self.is_full() == isinstance(self._state, FullState)
        assert not self._waitlist or self.is_full()
        assert bool(seated) != isinstance(self._state, ClosedState)
