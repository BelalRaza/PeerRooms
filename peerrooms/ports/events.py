from abc import ABC, abstractmethod


class EventPublisher(ABC):
    """The write-only event interface injected into services."""

    @abstractmethod
    def publish(self, event: object) -> None: ...


class EventListener(ABC):
    """Observer contract for reacting to a published event."""

    @abstractmethod
    def handle(self, event: object) -> None: ...
