from collections.abc import Iterable, Mapping
from dataclasses import asdict

from peerrooms.app.views import (
    ConnectionView, JoinView, LeaveView, MemberView, MessageView, NotificationView,
    PeerView, PendingRequestsView, RequestView, RoomCardView, RoomDetailView, StudentView,
    WaitlistPositionView, interest_names, room_card, student_view,
)
from peerrooms.domain.connection import ConnectionRequest
from peerrooms.domain.enums import RoomStatus, RoomType
from peerrooms.domain.exceptions import ValidationError
from peerrooms.domain.message import Message
from peerrooms.services.connection_service import ConnectionService
from peerrooms.services.discovery_service import DiscoveryService
from peerrooms.services.notification_service import NotificationService
from peerrooms.services.room_service import RoomService
from peerrooms.services.student_service import StudentService
from peerrooms.strategies.matching import MatchingStrategy


class PeerRoomsApp:
    """Present one transport-independent entry point for every use case (Facade)."""

    def __init__(
        self, students: StudentService, rooms: RoomService, connections: ConnectionService,
        discovery: DiscoveryService, notifications: NotificationService,
        strategies: Mapping[str, MatchingStrategy],
    ) -> None:
        self._students, self._rooms, self._connections = students, rooms, connections
        self._discovery, self._notifications, self._strategies = discovery, notifications, dict(strategies)

    def register(
        self, name: str, email: str, department: str, year: int, interests: Iterable[str],
    ) -> StudentView:
        return student_view(self._students.register(name, email, department, year, interests))

    def sign_in(self, email: str) -> StudentView:
        return student_view(self._students.sign_in(email))

    def profile(self, student_id: str) -> StudentView:
        return student_view(self._students.profile(student_id))

    def update_interests(self, student_id: str, interests: Iterable[str]) -> StudentView:
        return student_view(self._students.update_interests(student_id, interests))

    def block_student(self, student_id: str, other_id: str) -> None:
        self._students.block_student(student_id, other_id)

    def list_rooms(
        self, student_id: str, tag: str | None = None, status: RoomStatus | None = None,
    ) -> list[RoomCardView]:
        self._students.profile(student_id)
        return [room_card(room, student_id) for room in self._rooms.list_rooms(tag, status)]

    def recommend_rooms(self, student_id: str, limit: int = 10) -> list[RoomCardView]:
        return [room_card(room, student_id) for room in self._discovery.recommend_rooms(student_id, limit)]

    def create_room(
        self, student_id: str, room_type: RoomType, topic: str, prompt: str,
        tags: Iterable[str], capacity: int | None = None,
    ) -> RoomCardView:
        return room_card(self._rooms.create_room(student_id, room_type, topic, prompt, tags, capacity), student_id)

    def room_detail(self, student_id: str, room_id: str) -> RoomDetailView:
        self._students.profile(student_id)
        room = self._rooms.room_detail(room_id)
        recent = room.messages[-50:]
        people = {member.student_id for member in room.members} | {message.sender_id for message in recent}
        names = {person: self._students.profile(person).name for person in people}
        return RoomDetailView(
            **asdict(room_card(room, student_id)),
            prompt=room.prompt,
            members=tuple(
                MemberView(member.student_id, names[member.student_id], member.role, member.joined_at)
                for member in room.members
            ),
            waitlist=tuple(
                WaitlistPositionView(position, waiting == student_id)
                for position, waiting in enumerate(room.waitlist, 1)
            ),
            messages=tuple(self._message_view(message, names[message.sender_id]) for message in recent),
        )

    def join_room(self, student_id: str, room_id: str) -> JoinView:
        outcome = self._rooms.join_room(student_id, room_id)
        return JoinView(outcome.result, outcome.position)

    def leave_room(self, student_id: str, room_id: str) -> LeaveView:
        outcome = self._rooms.leave_room(student_id, room_id)
        return LeaveView(outcome.promoted_id, outcome.new_host_id, outcome.closed)

    def remove_member(self, student_id: str, room_id: str, target_id: str) -> None:
        self._rooms.remove_member(student_id, room_id, target_id)

    def close_room(self, student_id: str, room_id: str) -> None:
        self._rooms.close_room(student_id, room_id)

    def post_message(self, student_id: str, room_id: str, content: str) -> MessageView:
        message = self._rooms.post_message(student_id, room_id, content)
        return self._message_view(message, self._students.profile(student_id).name)

    def suggest_peers(self, student_id: str, limit: int = 10, strategy: str | None = None) -> list[PeerView]:
        scorer = self._strategies.get(strategy) if strategy is not None else None
        if strategy is not None and scorer is None:
            choices = ", ".join(self._strategies)
            raise ValidationError(f"Unknown matching strategy: {strategy}. Choose {choices}.")
        return [
            PeerView(student_view(item.student), item.score, interest_names(item.common_interests))
            for item in self._discovery.suggest_peers(student_id, limit, scorer)
        ]

    def send_request(self, student_id: str, receiver_id: str) -> RequestView:
        return self._request_view(self._connections.send_request(student_id, receiver_id))

    def accept(self, student_id: str, request_id: str) -> ConnectionView:
        link = self._connections.accept(request_id, student_id)
        return ConnectionView(link.id, self.profile(link.other(student_id)), link.connected_at)

    def reject(self, student_id: str, request_id: str) -> RequestView:
        return self._request_view(self._connections.reject(request_id, student_id))

    def cancel(self, student_id: str, request_id: str) -> RequestView:
        return self._request_view(self._connections.cancel(request_id, student_id))

    def pending_requests(self, student_id: str) -> PendingRequestsView:
        requests = [self._request_view(request) for request in self._connections.pending_requests(student_id)]
        return PendingRequestsView(
            tuple(request for request in requests if request.receiver_id == student_id),
            tuple(request for request in requests if request.sender_id == student_id),
        )

    def network_of(self, student_id: str) -> list[StudentView]:
        return [student_view(student) for student in self._connections.network_of(student_id)]

    def inbox(self, student_id: str) -> list[NotificationView]:
        return [
            NotificationView(item.id, item.type, item.text, item.is_read, item.created_at)
            for item in self._notifications.inbox(student_id)
        ]

    def mark_read(self, student_id: str, notification_id: str) -> None:
        self._notifications.mark_read(notification_id, student_id)

    def _request_view(self, request: ConnectionRequest) -> RequestView:
        return RequestView(
            request.id, request.sender_id, self._students.profile(request.sender_id).name,
            request.receiver_id, self._students.profile(request.receiver_id).name,
            request.status, request.created_at, request.responded_at,
        )

    @staticmethod
    def _message_view(message: Message, sender_name: str) -> MessageView:
        return MessageView(message.id, message.room_id, message.sender_id, sender_name, message.content, message.sent_at)
