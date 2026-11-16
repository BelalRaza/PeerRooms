from _thread import LockType
from collections.abc import Callable
from datetime import datetime

from peerrooms.domain.connection import Connection, ConnectionRequest
from peerrooms.domain.events import ConnectionAccepted, ConnectionRequested
from peerrooms.domain.exceptions import (
    AlreadyConnectedError, BlockedError, DuplicateRequestError, ValidationError,
)
from peerrooms.domain.student import Student
from peerrooms.ports.clock import Clock
from peerrooms.ports.events import EventPublisher
from peerrooms.ports.repositories import (
    ConnectionRepository, ConnectionRequestRepository, StudentRepository,
)


class ConnectionService:
    """Coordinate unique pending requests and accepted network edges (FR10, FR11)."""

    def __init__(
        self, students: StudentRepository, requests: ConnectionRequestRepository,
        connections: ConnectionRepository, publisher: EventPublisher, clock: Clock,
        ids: Callable[[], str], writes: LockType,
    ) -> None:
        self._students, self._requests, self._connections = students, requests, connections
        self._publisher, self._clock, self._ids, self._writes = publisher, clock, ids, writes

    def send_request(self, sender_id: str, receiver_id: str) -> ConnectionRequest:
        with self._writes:
            sender = self._students.get(sender_id)
            receiver = self._students.get(receiver_id)
            if sender_id == receiver_id:
                raise ValidationError("You cannot send a connection request to yourself.")
            self._ensure_unblocked(sender, receiver)
            if self._connections.are_connected(sender_id, receiver_id):
                raise AlreadyConnectedError("You are already connected to this student.")
            pending = self._requests.pending_between(sender_id, receiver_id)
            if pending is not None:
                message = (
                    "They already sent you a request. Accept it from your network."
                    if pending.sender_id == receiver_id else "You already sent this student a request."
                )
                raise DuplicateRequestError(message)
            request = ConnectionRequest(self._ids(), sender_id, receiver_id, self._clock.now())
            self._requests.save(request)
        self._publisher.publish(ConnectionRequested(request.id, sender_id, receiver_id))
        return request

    def accept(self, request_id: str, by_id: str) -> Connection:
        with self._writes:
            self._students.get(by_id)
            request = self._requests.get(request_id)
            now = self._clock.now()
            request.accept(by_id, now)
            self._ensure_unblocked(
                self._students.get(request.sender_id), self._students.get(request.receiver_id),
            )
            connection = Connection(self._ids(), frozenset({request.sender_id, request.receiver_id}), now)
            self._requests.save(request)
            self._connections.save(connection)
        self._publisher.publish(ConnectionAccepted(request.id, request.sender_id, request.receiver_id))
        return connection

    def reject(self, request_id: str, by_id: str) -> ConnectionRequest:
        return self._respond(request_id, by_id, ConnectionRequest.reject)

    def cancel(self, request_id: str, by_id: str) -> ConnectionRequest:
        return self._respond(request_id, by_id, ConnectionRequest.cancel)

    def network_of(self, student_id: str) -> list[Student]:
        self._students.get(student_id)
        with self._writes:
            network = [
                self._students.get(connection.other(student_id))
                for connection in self._connections.connections_of(student_id)
            ]
        return sorted(network, key=lambda student: (student.name.casefold(), student.email))

    def pending_requests(self, student_id: str) -> list[ConnectionRequest]:
        self._students.get(student_id)
        with self._writes:
            requests = self._requests.pending_for(student_id)
        return sorted(requests, key=lambda request: (request.created_at, request.id), reverse=True)

    def _respond(
        self, request_id: str, by_id: str, action: Callable[[ConnectionRequest, str, datetime], None],
    ) -> ConnectionRequest:
        with self._writes:
            self._students.get(by_id)
            request = self._requests.get(request_id)
            action(request, by_id, self._clock.now())
            self._requests.save(request)
        return request

    @staticmethod
    def _ensure_unblocked(sender: Student, receiver: Student) -> None:
        if sender.blocks(receiver.id) or receiver.blocks(sender.id):
            raise BlockedError("This pair cannot exchange connection requests.")
