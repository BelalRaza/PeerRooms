from copy import deepcopy
from threading import Lock
from typing import Generic, TypeVar

from peerrooms.domain.connection import Connection, ConnectionRequest
from peerrooms.domain.enums import RequestStatus
from peerrooms.domain.exceptions import (
    NotificationNotFoundError, RequestNotFoundError, RoomNotFoundError,
    StudentNotFoundError,
)
from peerrooms.domain.notification import Notification
from peerrooms.domain.room import Room
from peerrooms.domain.student import Student, normalize_email
from peerrooms.ports.repositories import (
    ConnectionRepository, ConnectionRequestRepository, NotificationRepository,
    RoomRepository, StudentRepository,
)

K = TypeVar("K")
V = TypeVar("V")


class _MemoryStore(Generic[K, V]):
    """Publish detached snapshots with short, synchronized dictionary access."""

    def __init__(self) -> None:
        self._data: dict[K, V] = {}
        self._guard = Lock()

    def _save(self, key: K, value: V) -> None:
        snapshot = deepcopy(value)
        with self._guard:
            self._data[key] = snapshot

    def _get(self, key: K) -> V | None:
        with self._guard:
            snapshot = self._data.get(key)
        return deepcopy(snapshot)

    def _values(self) -> tuple[V, ...]:
        with self._guard:
            return tuple(self._data.values())


class InMemoryStudentRepository(_MemoryStore[str, Student], StudentRepository):
    """Keep profiles in a synchronized memory store (Repository)."""

    def save(self, student: Student) -> None:
        self._save(student.id, student)

    def get(self, student_id: str) -> Student:
        student = self._get(student_id)
        if student is None:
            raise StudentNotFoundError(f"Student {student_id} was not found.")
        return student

    def find_by_email(self, email: str) -> Student:
        normalized = normalize_email(email)
        for student in self._values():
            if student.email == normalized:
                return deepcopy(student)
        raise StudentNotFoundError(f"No student is registered with {normalized}.")

    def all(self) -> list[Student]:
        return [deepcopy(student) for student in self._values()]


class InMemoryRoomRepository(_MemoryStore[str, Room], RoomRepository):
    """Keep active and closed rooms, including their participation history."""

    def save(self, room: Room) -> None:
        self._save(room.id, room)

    def get(self, room_id: str) -> Room:
        room = self._get(room_id)
        if room is None:
            raise RoomNotFoundError(f"Room {room_id} was not found.")
        return room

    def all(self) -> list[Room]:
        return [deepcopy(room) for room in self._values()]

    def rooms_of(self, student_id: str) -> list[Room]:
        return [deepcopy(room) for room in self._values() if student_id in room.past_participants]


class InMemoryConnectionRequestRepository(
    _MemoryStore[str, ConnectionRequest], ConnectionRequestRepository,
):
    """Keep pending requests and all terminal history by ID."""

    def save(self, request: ConnectionRequest) -> None:
        self._save(request.id, request)

    def get(self, request_id: str) -> ConnectionRequest:
        request = self._get(request_id)
        if request is None:
            raise RequestNotFoundError(f"Request {request_id} was not found.")
        return request

    def pending_between(self, a_id: str, b_id: str) -> ConnectionRequest | None:
        for request in self.pending_for(a_id):
            if {request.sender_id, request.receiver_id} == {a_id, b_id}:
                return request
        return None

    def pending_for(self, student_id: str) -> list[ConnectionRequest]:
        return [
            deepcopy(request) for request in self._values()
            if request.status is RequestStatus.PENDING
            and student_id in (request.sender_id, request.receiver_id)
        ]


class InMemoryConnectionRepository(_MemoryStore[frozenset[str], Connection], ConnectionRepository):
    """Index accepted edges by an order-independent pair of student IDs."""

    def save(self, connection: Connection) -> None:
        self._save(connection.student_ids, connection)

    def are_connected(self, a_id: str, b_id: str) -> bool:
        with self._guard:
            return frozenset({a_id, b_id}) in self._data

    def connections_of(self, student_id: str) -> list[Connection]:
        return [connection for connection in self._values() if student_id in connection.student_ids]


class InMemoryNotificationRepository(_MemoryStore[str, Notification], NotificationRepository):
    """Store inbox messages by ID and filter by recipient."""

    def save(self, notification: Notification) -> None:
        self._save(notification.id, notification)

    def get(self, notification_id: str) -> Notification:
        notification = self._get(notification_id)
        if notification is None:
            raise NotificationNotFoundError(f"Notification {notification_id} was not found.")
        return notification

    def for_student(self, student_id: str) -> list[Notification]:
        return [deepcopy(item) for item in self._values() if item.recipient_id == student_id]
