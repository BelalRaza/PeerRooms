from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType

from peerrooms.domain.enums import RoomType
from peerrooms.domain.exceptions import InvalidCapacityError, ValidationError
from peerrooms.domain.interest import Interest
from peerrooms.domain.room import Room


@dataclass(frozen=True, slots=True)
class RoomTypeConfig:
    """Default, minimum, and maximum seats for a room type."""

    default_capacity: int
    min_capacity: int
    max_capacity: int


ROOM_TYPE_CONFIG: Mapping[RoomType, RoomTypeConfig] = MappingProxyType({
    RoomType.QUICK_CHAT: RoomTypeConfig(4, 2, 4),
    RoomType.DISCUSSION: RoomTypeConfig(6, 4, 8),
    RoomType.PANEL: RoomTypeConfig(12, 8, 20),
})


class RoomFactory:
    """Build rooms using the capacity registry (Factory, FR3)."""

    def __init__(
        self, ids: Callable[[], str], configs: Mapping[RoomType, RoomTypeConfig] = ROOM_TYPE_CONFIG,
    ) -> None:
        self._ids = ids
        self._configs = dict(configs)

    def create(
        self, room_type: RoomType, topic: str, prompt: str, tags: Iterable[str],
        host_id: str, now: datetime, capacity: int | None = None,
    ) -> Room:
        config = self._configs.get(room_type)
        if config is None:
            raise ValidationError(f"Unknown room type: {room_type}.")
        seats = config.default_capacity if capacity is None else capacity
        if type(seats) is not int or not config.min_capacity <= seats <= config.max_capacity:
            raise InvalidCapacityError(
                f"{room_type} requires {config.min_capacity} to {config.max_capacity} seats."
            )
        return Room(
            self._ids(), topic, prompt, frozenset(Interest.of(tag) for tag in tags),
            room_type, seats, host_id, now,
        )
