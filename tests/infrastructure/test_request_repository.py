import pytest

from tests.helpers import NOW
from peerrooms.domain.connection import ConnectionRequest
from peerrooms.domain.enums import RequestStatus
from peerrooms.domain.exceptions import RequestNotFoundError
from peerrooms.infrastructure.in_memory_repositories import InMemoryConnectionRequestRepository


def test_pending_is_symmetric_and_terminal_history_is_preserved() -> None:
    repo = InMemoryConnectionRequestRepository()
    request = ConnectionRequest("r", "A", "B", NOW)
    repo.save(request)
    assert repo.pending_between("A", "B").id == repo.pending_between("B", "A").id == "r"
    assert not repo.pending_for("C")
    request.reject("B", NOW)
    assert repo.get("r").status is RequestStatus.PENDING
    repo.save(request)
    assert repo.get("r").status is RequestStatus.REJECTED
    assert repo.pending_between("A", "B") is None
    with pytest.raises(RequestNotFoundError):
        repo.get("missing")
