from datetime import UTC, datetime

from peerrooms.app.facade import PeerRoomsApp
from peerrooms.app.views import RoomCardView, StudentView
from peerrooms.domain.enums import RoomType
from peerrooms.domain.interest import Interest
from peerrooms.domain.student import Student

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def student(name: str, *interests: str) -> Student:
    return Student(
        name, name, f"{name.lower()}@college.edu", "CS", 2,
        frozenset(Interest.of(value) for value in (interests or ("ai",))),
    )


def register(app: PeerRoomsApp, name: str, *interests: str) -> StudentView:
    handle = ".".join(name.lower().split())
    return app.register(name, f"{handle}@college.edu", "CS", 2, interests or ("ai",))


def quick_room(
    app: PeerRoomsApp, host_id: str, topic: str = "Campus AI", capacity: int = 3,
    tags: tuple[str, ...] = ("ai",),
) -> RoomCardView:
    return app.create_room(host_id, RoomType.QUICK_CHAT, topic, "What should we build?", tags, capacity)
