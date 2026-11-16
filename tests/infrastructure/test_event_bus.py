from peerrooms.domain.events import RoomCreated, StudentLeft
from peerrooms.infrastructure.event_bus import EventBus
from peerrooms.ports.events import EventListener


class RecordingListener(EventListener):
    """Capture dispatched events for assertions."""

    def __init__(self) -> None:
        self.events: list[object] = []

    def handle(self, event: object) -> None:
        self.events.append(event)


def test_two_observers_get_only_subscribed_event_types() -> None:
    bus = EventBus()
    first, second = RecordingListener(), RecordingListener()
    bus.subscribe(RoomCreated, first)
    bus.subscribe(RoomCreated, second)
    bus.subscribe(StudentLeft, second)
    created, left = RoomCreated("r", "h"), StudentLeft("r", "h")
    bus.publish(created)
    bus.publish(left)
    bus.publish(object())
    assert first.events == [created]
    assert second.events == [created, left]
