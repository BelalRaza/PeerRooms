from abc import ABC, abstractmethod
from collections.abc import Sequence
from math import isclose, isfinite

from peerrooms.domain.exceptions import ValidationError
from peerrooms.domain.interest import Interest
from peerrooms.domain.student import Student
from peerrooms.ports.repositories import RoomRepository


def jaccard(first: frozenset[Interest], second: frozenset[Interest]) -> float:
    union = first | second
    return len(first & second) / len(union) if union else 0.0


class MatchingStrategy(ABC):
    """Calculate a similarity score for two students (Strategy)."""

    @abstractmethod
    def score(self, me: Student, other: Student) -> float: ...


class JaccardInterestStrategy(MatchingStrategy):
    """Score the overlap of normalized student interests."""

    def score(self, me: Student, other: Student) -> float:
        return jaccard(me.interests, other.interests)


class SharedRoomsStrategy(MatchingStrategy):
    """Score shared room history, saturating at five rooms."""

    def __init__(self, rooms: RoomRepository) -> None:
        self._rooms = rooms

    def score(self, me: Student, other: Student) -> float:
        mine = {room.id for room in self._rooms.rooms_of(me.id)}
        theirs = {room.id for room in self._rooms.rooms_of(other.id)}
        return min(len(mine & theirs), 5) / 5


class WeightedStrategy(MatchingStrategy):
    """Combine interchangeable strategies as a weighted Composite."""

    def __init__(self, parts: Sequence[tuple[MatchingStrategy, float]]) -> None:
        if any(not isfinite(weight) or weight < 0 for _, weight in parts) or not isclose(
            sum(weight for _, weight in parts), 1.0, rel_tol=0.0, abs_tol=1e-9,
        ):
            raise ValidationError("Matching weights must be nonnegative and sum to 1.")
        self._parts = tuple(parts)

    def score(self, me: Student, other: Student) -> float:
        return sum(weight * strategy.score(me, other) for strategy, weight in self._parts)
