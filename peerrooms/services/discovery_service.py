from _thread import LockType
from dataclasses import dataclass

from peerrooms.domain.enums import RoomStatus
from peerrooms.domain.exceptions import ValidationError
from peerrooms.domain.interest import Interest
from peerrooms.domain.room import Room
from peerrooms.domain.student import Student
from peerrooms.ports.repositories import (
    ConnectionRepository, ConnectionRequestRepository, RoomRepository, StudentRepository,
)
from peerrooms.strategies.matching import MatchingStrategy, jaccard


@dataclass(frozen=True, slots=True)
class PeerSuggestion:
    """A ranked peer and the shared interests that explain the suggestion."""

    student: Student
    score: float
    common_interests: frozenset[Interest]


class DiscoveryService:
    """Rank eligible peers and rooms using injected scoring and repositories."""

    def __init__(
        self, students: StudentRepository, rooms: RoomRepository, connections: ConnectionRepository,
        requests: ConnectionRequestRepository, default_strategy: MatchingStrategy, writes: LockType,
    ) -> None:
        self._students, self._rooms = students, rooms
        self._connections, self._requests = connections, requests
        self._default_strategy, self._writes = default_strategy, writes

    def suggest_peers(
        self, student_id: str, limit: int = 10, strategy: MatchingStrategy | None = None,
    ) -> list[PeerSuggestion]:
        self._validate_limit(limit)
        scorer = strategy if strategy is not None else self._default_strategy
        with self._writes:
            me = self._students.get(student_id)
            excluded = {student_id}
            excluded.update(link.other(student_id) for link in self._connections.connections_of(student_id))
            for pending in self._requests.pending_for(student_id):
                excluded.update((pending.sender_id, pending.receiver_id))
            candidates = self._students.all()

        suggestions: list[PeerSuggestion] = []
        for candidate in candidates:
            if candidate.id in excluded or me.blocks(candidate.id) or candidate.blocks(me.id):
                continue
            score = scorer.score(me, candidate)
            if score > 0:
                suggestions.append(PeerSuggestion(candidate, score, me.common_interests(candidate)))

        suggestions.sort(key=lambda item: (
            -item.score, -len(item.common_interests), item.student.name.casefold(), item.student.email,
        ))
        return suggestions[:limit]

    def recommend_rooms(self, student_id: str, limit: int = 10) -> list[Room]:
        self._validate_limit(limit)
        student = self._students.get(student_id)
        rooms = [
            room for room in self._rooms.all()
            if room.status() is not RoomStatus.CLOSED
            and not room.is_member(student_id)
            and student_id not in room.waitlist
        ]
        rooms.sort(key=lambda room: (
            -jaccard(student.interests, room.tags), room.status() is not RoomStatus.OPEN,
            -room.created_at.timestamp(), room.id,
        ))
        return rooms[:limit]

    @staticmethod
    def _validate_limit(limit: int) -> None:
        if type(limit) is not int or limit < 1:
            raise ValidationError("Limit must be a positive integer.")
