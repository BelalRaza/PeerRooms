from abc import ABC, abstractmethod

from peerrooms.domain.connection import Connection, ConnectionRequest
from peerrooms.domain.notification import Notification
from peerrooms.domain.room import Room
from peerrooms.domain.student import Student


class StudentRepository(ABC):
    """Student persistence port with exact-ID and email lookups."""

    @abstractmethod
    def save(self, student: Student) -> None: ...

    @abstractmethod
    def get(self, student_id: str) -> Student: ...

    @abstractmethod
    def find_by_email(self, email: str) -> Student: ...

    @abstractmethod
    def all(self) -> list[Student]: ...


class RoomRepository(ABC):
    """Room aggregate persistence, including historical participation."""

    @abstractmethod
    def save(self, room: Room) -> None: ...

    @abstractmethod
    def get(self, room_id: str) -> Room: ...

    @abstractmethod
    def all(self) -> list[Room]: ...

    @abstractmethod
    def rooms_of(self, student_id: str) -> list[Room]: ...


class ConnectionRequestRepository(ABC):
    """Request persistence with symmetric pending-request queries."""

    @abstractmethod
    def save(self, request: ConnectionRequest) -> None: ...

    @abstractmethod
    def get(self, request_id: str) -> ConnectionRequest: ...

    @abstractmethod
    def pending_between(self, a_id: str, b_id: str) -> ConnectionRequest | None: ...

    @abstractmethod
    def pending_for(self, student_id: str) -> list[ConnectionRequest]: ...


class ConnectionRepository(ABC):
    """Accepted network edges keyed by unordered pairs."""

    @abstractmethod
    def save(self, connection: Connection) -> None: ...

    @abstractmethod
    def are_connected(self, a_id: str, b_id: str) -> bool: ...

    @abstractmethod
    def connections_of(self, student_id: str) -> list[Connection]: ...


class NotificationRepository(ABC):
    """Persistence port for a student's inbox and individual items."""

    @abstractmethod
    def save(self, notification: Notification) -> None: ...

    @abstractmethod
    def get(self, notification_id: str) -> Notification: ...

    @abstractmethod
    def for_student(self, student_id: str) -> list[Notification]: ...
