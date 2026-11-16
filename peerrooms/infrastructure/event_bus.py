from collections import defaultdict
from threading import Lock

from peerrooms.ports.events import EventListener, EventPublisher


class EventBus(EventPublisher):
    """Deliver events synchronously to registered Observer listeners."""

    def __init__(self) -> None:
        self._listeners: dict[type[object], list[EventListener]] = defaultdict(list)
        self._guard = Lock()

    def subscribe(self, event_type: type[object], listener: EventListener) -> None:
        with self._guard:
            self._listeners[event_type].append(listener)

    def publish(self, event: object) -> None:
        with self._guard:
            listeners = tuple(self._listeners.get(type(event), ()))
        for listener in listeners:
            listener.handle(event)
