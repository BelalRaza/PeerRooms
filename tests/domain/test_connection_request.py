from datetime import timedelta

import pytest

from tests.helpers import NOW
from peerrooms.domain.connection import Connection, ConnectionRequest
from peerrooms.domain.enums import RequestStatus
from peerrooms.domain.exceptions import InvalidTransitionError, PermissionDeniedError, ValidationError


@pytest.mark.parametrize(("method", "actor", "expected"), [
    ("accept", "B", RequestStatus.ACCEPTED),
    ("reject", "B", RequestStatus.REJECTED),
    ("cancel", "A", RequestStatus.CANCELLED),
])
def test_transitions_are_terminal(method: str, actor: str, expected: RequestStatus) -> None:
    request = ConnectionRequest("r", "A", "B", NOW)
    assert request.status is RequestStatus.PENDING and request.responded_at is None
    later = NOW + timedelta(minutes=2)
    getattr(request, method)(actor, later)
    assert (request.status, request.responded_at) == (expected, later)
    for action in (request.accept, request.reject):
        with pytest.raises(InvalidTransitionError):
            action("B", NOW)
    with pytest.raises(InvalidTransitionError):
        request.cancel("A", NOW)


def test_only_the_correct_actor_can_respond() -> None:
    request = ConnectionRequest("r", "A", "B", NOW)
    for action, wrong_actor in [(request.accept, "A"), (request.reject, "A"), (request.cancel, "B")]:
        with pytest.raises(PermissionDeniedError):
            action(wrong_actor, NOW)
    assert request.status is RequestStatus.PENDING


def test_connection_requires_two_participants() -> None:
    with pytest.raises(ValidationError):
        Connection("c", frozenset({"A"}), NOW)
    with pytest.raises(ValidationError):
        ConnectionRequest("r", "A", "A", NOW)
    pair = Connection("c", frozenset({"B", "A"}), NOW)
    assert pair.other("A") == "B" and pair.other("B") == "A"
    with pytest.raises(ValidationError):
        pair.other("C")
