from _thread import LockType

import pytest

from tests.helpers import student
from peerrooms.domain.enums import JoinResult, RoomStatus, RoomType
from peerrooms.domain.events import (
    HostChanged, MemberRemoved, MessagePosted, RoomClosed, RoomCreated, StudentJoined,
    StudentLeft, StudentPromoted, StudentWaitlisted,
)
from peerrooms.domain.exceptions import InvalidCapacityError, RoomNotFoundError, ValidationError
from peerrooms.factories.room_factory import RoomFactory
from peerrooms.infrastructure.clocks import FakeClock
from peerrooms.infrastructure.event_bus import EventBus
from peerrooms.infrastructure.ids import new_id
from peerrooms.infrastructure.in_memory_repositories import InMemoryRoomRepository, InMemoryStudentRepository
from peerrooms.ports.events import EventListener
from peerrooms.services.room_service import RoomService


class RoomRecorder(EventListener):
    """Record events and prove handlers can take the room's lock."""

    def __init__(self, service: RoomService) -> None:
        self.service = service
        self.events: list[object] = []

    def handle(self, event: object) -> None:
        lock: LockType = self.service._lock_for(event.room_id)
        assert lock.acquire(blocking=False), "Event was sent with the room lock still held"
        lock.release()
        self.events.append(event)


def test_room_operations_publish_after_save_and_unlock(clock: FakeClock) -> None:
    rooms, students, bus = InMemoryRoomRepository(), InMemoryStudentRepository(), EventBus()
    for identifier in "HABC":
        students.save(student(identifier))
    service = RoomService(rooms, students, RoomFactory(new_id), bus, clock)
    recorder = RoomRecorder(service)
    for event_type in (
        RoomCreated, StudentJoined, StudentWaitlisted, StudentLeft, StudentPromoted, HostChanged,
        MemberRemoved, MessagePosted, RoomClosed,
    ):
        bus.subscribe(event_type, recorder)

    identifier = service.create_room("H", RoomType.QUICK_CHAT, "AI", "hello", ["AI"], 2).id
    assert service.join_room("A", identifier).result is JoinResult.JOINED
    assert service.join_room("B", identifier).position == 1
    assert service.join_room("C", identifier).position == 2
    message = service.post_message("A", identifier, "Hello")
    service.leave_room("H", identifier)
    assert service.room_detail(identifier).host_id == "A"
    service.remove_member("A", identifier, "B")
    assert service.room_detail(identifier).is_member("C")
    service.join_room("H", identifier)
    service.close_room("A", identifier)
    assert service.room_detail(identifier).status() is RoomStatus.CLOSED
    assert not service.list_rooms()
    assert [room.id for room in service.list_rooms(" AI ", RoomStatus.CLOSED)] == [identifier]
    assert recorder.events == [
        RoomCreated(identifier, "H"), StudentJoined(identifier, "A", "H"),
        StudentWaitlisted(identifier, "B", "H"), StudentWaitlisted(identifier, "C", "H"),
        MessagePosted(identifier, "A", message.id), StudentLeft(identifier, "H"),
        StudentPromoted(identifier, "B"), HostChanged(identifier, "A"),
        MemberRemoved(identifier, "B"), StudentPromoted(identifier, "C"),
        StudentWaitlisted(identifier, "H", "A"), RoomClosed(identifier, ("C", "H")),
    ]
    with pytest.raises(RoomNotFoundError):
        service.join_room("A", "unknown")


@pytest.mark.parametrize(("kind", "minimum", "default", "maximum"), [
    (RoomType.QUICK_CHAT, 2, 4, 4), (RoomType.DISCUSSION, 4, 6, 8), (RoomType.PANEL, 8, 12, 20),
])
def test_room_factory_ranges(
    clock: FakeClock, kind: RoomType, minimum: int, default: int, maximum: int,
) -> None:
    factory = RoomFactory(new_id)

    def build(capacity: int | None = None) -> int:
        return factory.create(kind, "Topic", "Prompt", ["tag"], "H", clock.now(), capacity).capacity

    assert (build(minimum), build(), build(maximum)) == (minimum, default, maximum)
    for capacity in (minimum - 1, maximum + 1, True):
        with pytest.raises(InvalidCapacityError):
            build(capacity)
    with pytest.raises(ValidationError):
        factory.create(kind, "", "Prompt", ["tag"], "H", clock.now())
