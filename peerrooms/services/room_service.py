from _thread import LockType
from collections.abc import Iterable
from threading import Lock

from peerrooms.domain.enums import JoinResult, RoomStatus, RoomType
from peerrooms.domain.events import (
    HostChanged, MemberRemoved, MessagePosted, RoomClosed, RoomCreated, StudentJoined,
    StudentLeft, StudentPromoted, StudentWaitlisted,
)
from peerrooms.domain.interest import Interest
from peerrooms.domain.message import Message
from peerrooms.domain.room import JoinOutcome, LeaveResult, Room
from peerrooms.factories.room_factory import RoomFactory
from peerrooms.ports.clock import Clock
from peerrooms.ports.events import EventPublisher
from peerrooms.ports.repositories import RoomRepository, StudentRepository


class RoomService:
    """Run room use cases with per-room write locks and post-commit events."""

    def __init__(
        self, rooms: RoomRepository, students: StudentRepository, factory: RoomFactory,
        publisher: EventPublisher, clock: Clock,
    ) -> None:
        self._rooms, self._students, self._factory = rooms, students, factory
        self._publisher, self._clock = publisher, clock
        self._locks: dict[str, LockType] = {}
        self._locks_guard = Lock()

    def create_room(
        self, host_id: str, room_type: RoomType, topic: str, prompt: str,
        tags: Iterable[str], capacity: int | None = None,
    ) -> Room:
        self._students.get(host_id)
        room = self._factory.create(room_type, topic, prompt, tags, host_id, self._clock.now(), capacity)
        self._rooms.save(room)
        with self._locks_guard:
            self._locks.setdefault(room.id, Lock())
        self._publisher.publish(RoomCreated(room.id, host_id))
        return room

    def list_rooms(self, tag: str | None = None, status: RoomStatus | None = None) -> list[Room]:
        interest = Interest.of(tag) if tag is not None else None
        rooms = [
            room for room in self._rooms.all()
            if (room.status() is status if status is not None else room.status() is not RoomStatus.CLOSED)
            and (interest is None or interest in room.tags)
        ]
        return sorted(rooms, key=lambda room: (room.created_at, room.id), reverse=True)

    def room_detail(self, room_id: str) -> Room:
        return self._rooms.get(room_id)

    def join_room(self, student_id: str, room_id: str) -> JoinOutcome:
        self._students.get(student_id)
        with self._lock_for(room_id):
            room = self._rooms.get(room_id)
            result = room.join(student_id, self._clock.now())
            self._rooms.save(room)
        assert room.host_id is not None
        event_type = StudentJoined if result.result is JoinResult.JOINED else StudentWaitlisted
        self._publisher.publish(event_type(room_id, student_id, room.host_id))
        return result

    def leave_room(self, student_id: str, room_id: str) -> LeaveResult:
        self._students.get(student_id)
        with self._lock_for(room_id):
            room = self._rooms.get(room_id)
            result = room.leave(student_id, self._clock.now())
            self._rooms.save(room)
        self._publisher.publish(StudentLeft(room_id, student_id))
        self._publish_leave_events(room_id, result)
        return result

    def remove_member(self, host_id: str, room_id: str, target_id: str) -> None:
        self._students.get(host_id)
        self._students.get(target_id)
        with self._lock_for(room_id):
            room = self._rooms.get(room_id)
            result = room.remove_member(host_id, target_id, self._clock.now())
            self._rooms.save(room)
        self._publisher.publish(MemberRemoved(room_id, target_id))
        self._publish_leave_events(room_id, result)

    def close_room(self, host_id: str, room_id: str) -> None:
        self._students.get(host_id)
        with self._lock_for(room_id):
            room = self._rooms.get(room_id)
            recipients = tuple(
                member.student_id for member in room.members if member.student_id != host_id
            ) + room.waitlist
            room.close(host_id)
            self._rooms.save(room)
        self._publisher.publish(RoomClosed(room_id, recipients))

    def post_message(self, student_id: str, room_id: str, content: str) -> Message:
        self._students.get(student_id)
        with self._lock_for(room_id):
            room = self._rooms.get(room_id)
            message = room.post_message(student_id, content, self._clock.now())
            self._rooms.save(room)
        self._publisher.publish(MessagePosted(room_id, student_id, message.id))
        return message

    def _lock_for(self, room_id: str) -> LockType:
        with self._locks_guard:
            lock = self._locks.get(room_id)
            if lock is None:
                self._rooms.get(room_id)
                lock = self._locks[room_id] = Lock()
            return lock

    def _publish_leave_events(self, room_id: str, result: LeaveResult) -> None:
        if result.promoted_id is not None:
            self._publisher.publish(StudentPromoted(room_id, result.promoted_id))
        if result.new_host_id is not None:
            self._publisher.publish(HostChanged(room_id, result.new_host_id))
        if result.closed:
            self._publisher.publish(RoomClosed(room_id))
