from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from typing import TypeVar

from tests.helpers import quick_room, register
from peerrooms.app.facade import PeerRoomsApp
from peerrooms.domain.enums import JoinResult, RoomStatus
from peerrooms.domain.exceptions import DuplicateEmailError, DuplicateRequestError

T = TypeVar("T")


def simultaneous(actions: list[Callable[[], T]]) -> list[T]:
    barrier = Barrier(len(actions))

    def start(action: Callable[[], T]) -> T:
        barrier.wait(timeout=5)
        return action()

    with ThreadPoolExecutor(max_workers=len(actions)) as pool:
        return list(pool.map(start, actions))


def test_ten_simultaneous_joins_leave_only_two_new_seats(application: PeerRoomsApp) -> None:
    host = register(application, "Host")
    room = quick_room(application, host.id)
    guests = [register(application, f"Guest{index}") for index in range(10)]
    outcomes = simultaneous([
        lambda student_id=guest.id: application.join_room(student_id, room.id) for guest in guests
    ])
    detail = application.room_detail(host.id, room.id)
    seated = {member.student_id for member in detail.members}
    waiting = {
        guest.id for guest in guests
        if application.room_detail(guest.id, room.id).viewer_waitlist_position is not None
    }
    assert detail.status is RoomStatus.FULL
    assert detail.seated_count == len(seated) == 3 and host.id in seated
    assert len(detail.waitlist) == len(waiting) == 8 and seated.isdisjoint(waiting)
    assert sum(result.result is JoinResult.JOINED for result in outcomes) == 2
    assert sorted(result.position for result in outcomes if result.position) == list(range(1, 9))


def test_registration_and_reciprocal_requests_are_atomic(application: PeerRoomsApp) -> None:
    def sign_up() -> str:
        try:
            return register(application, "Same").id
        except DuplicateEmailError:
            return "duplicate"

    signups = simultaneous([sign_up, sign_up])
    assert signups.count("duplicate") == 1
    me = application.sign_in("same@college.edu")
    other = register(application, "Other")

    def send(sender: str, receiver: str) -> str:
        try:
            return application.send_request(sender, receiver).id
        except DuplicateRequestError:
            return "duplicate"

    sent = simultaneous([lambda: send(me.id, other.id), lambda: send(other.id, me.id)])
    assert sent.count("duplicate") == 1
    requests = application.pending_requests(me.id)
    assert len(requests.incoming + requests.outgoing) == 1
