import pytest

from tests.helpers import register
from peerrooms.app.facade import PeerRoomsApp
from peerrooms.domain.enums import RequestStatus
from peerrooms.domain.exceptions import (
    AlreadyConnectedError, BlockedError, DuplicateEmailError, DuplicateRequestError, InvalidTransitionError,
    PermissionDeniedError, RequestNotFoundError, StudentNotFoundError, ValidationError,
)


def test_registration_email_unique_and_sign_in(application: PeerRoomsApp) -> None:
    maya = register(application, "Maya", "AI", " ai", "python")
    assert application.sign_in(" MAYA@COLLEGE.EDU ") == maya
    with pytest.raises(DuplicateEmailError):
        application.register("Other", " MAYA@COLLEGE.EDU ", "Physics", 4, ["design"])
    with pytest.raises(StudentNotFoundError):
        application.sign_in("unknown@college.edu")
    assert application.update_interests(maya.id, [" Rust ", "rust"]).interests == ("rust",)


def test_connections_are_unique_and_accepted_by_receiver(application: PeerRoomsApp) -> None:
    a, b = (register(application, name) for name in ("A", "B"))
    with pytest.raises(ValidationError):
        application.send_request(a.id, a.id)
    with pytest.raises(StudentNotFoundError):
        application.send_request(a.id, "unknown")
    with pytest.raises(RequestNotFoundError):
        application.accept(a.id, "unknown")
    outgoing = application.send_request(a.id, b.id)
    assert application.pending_requests(a.id).outgoing == (outgoing,)
    assert application.pending_requests(b.id).incoming == (outgoing,)
    with pytest.raises(DuplicateRequestError, match="already sent"):
        application.send_request(a.id, b.id)
    with pytest.raises(DuplicateRequestError, match="They already sent you"):
        application.send_request(b.id, a.id)
    with pytest.raises(PermissionDeniedError):
        application.accept(a.id, outgoing.id)
    assert application.accept(b.id, outgoing.id).student == a
    assert application.network_of(a.id) == [b] and application.network_of(b.id) == [a]
    assert application.pending_requests(a.id).outgoing == ()
    with pytest.raises(AlreadyConnectedError):
        application.send_request(b.id, a.id)


def test_rejected_and_cancelled_requests_can_be_retried(application: PeerRoomsApp) -> None:
    a, b = (register(application, name) for name in ("A", "B"))
    first = application.send_request(a.id, b.id)
    assert application.reject(b.id, first.id).status is RequestStatus.REJECTED
    with pytest.raises(InvalidTransitionError):
        application.accept(b.id, first.id)
    second = application.send_request(a.id, b.id)
    assert second.id != first.id
    assert application.cancel(a.id, second.id).status is RequestStatus.CANCELLED
    with pytest.raises(InvalidTransitionError):
        application.accept(b.id, second.id)
    assert application.send_request(b.id, a.id).status is RequestStatus.PENDING


def test_blocked_pair_cannot_exchange_or_accept_requests(application: PeerRoomsApp) -> None:
    a, b = (register(application, name) for name in ("A", "B"))
    pending = application.send_request(a.id, b.id)
    application.block_student(b.id, a.id)
    with pytest.raises(BlockedError):
        application.accept(b.id, pending.id)
    assert application.reject(b.id, pending.id).status is RequestStatus.REJECTED
    for sender, receiver in [(a, b), (b, a)]:
        with pytest.raises(BlockedError):
            application.send_request(sender.id, receiver.id)
        assert application.suggest_peers(sender.id) == []
