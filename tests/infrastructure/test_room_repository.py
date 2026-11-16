import pytest

from tests.helpers import NOW
from peerrooms.domain.enums import RoomStatus
from peerrooms.domain.exceptions import RoomNotFoundError
from peerrooms.domain.room import Room
from peerrooms.infrastructure.in_memory_repositories import InMemoryRoomRepository


def test_room_snapshots_and_closed_history(room: Room) -> None:
    repo = InMemoryRoomRepository()
    repo.save(room)
    room.join("A", NOW)
    assert not repo.get(room.id).is_member("A")
    repo.save(room)
    stored = repo.get(room.id)
    stored.close("H")
    assert repo.get(room.id).status() is RoomStatus.OPEN
    repo.save(stored)
    assert [item.id for item in repo.rooms_of("A")] == [room.id]
    assert not repo.rooms_of("missing")
    assert repo.all()[0].status() is RoomStatus.CLOSED
    with pytest.raises(RoomNotFoundError):
        repo.get("missing")
