from abc import ABC, abstractmethod
from datetime import datetime


class Clock(ABC):
    """Time source for repeatable timestamp-based behavior."""

    @abstractmethod
    def now(self) -> datetime: ...
