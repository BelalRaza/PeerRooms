import pytest

from peerrooms.app.bootstrap import build_app
from peerrooms.app.facade import PeerRoomsApp
from peerrooms.domain.enums import RoomType
from peerrooms.domain.interest import Interest
from peerrooms.domain.room import Room
from peerrooms.infrastructure.clocks import FakeClock

from tests.helpers import NOW


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock(NOW)


@pytest.fixture
def application(clock: FakeClock) -> PeerRoomsApp:
    return build_app(clock)


@pytest.fixture
def room() -> Room:
    return Room("r", "Campus AI", "What should we build?", frozenset({Interest.of("ai")}),
                RoomType.QUICK_CHAT, 3, "H", NOW)
