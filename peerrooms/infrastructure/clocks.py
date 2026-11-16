from datetime import UTC, datetime, timedelta
from threading import Lock

from peerrooms.ports.clock import Clock


class SystemClock(Clock):
    """Return the current UTC time for the running app."""

    def now(self) -> datetime:
        return datetime.now(UTC)


class FakeClock(Clock):
    """Provide a controllable, deterministic time in tests."""

    def __init__(self, start: datetime | None = None) -> None:
        self._time = start or datetime(2026, 1, 1, tzinfo=UTC)
        self._guard = Lock()

    def now(self) -> datetime:
        with self._guard:
            return self._time

    def advance(self, minutes: float) -> None:
        with self._guard:
            self._time += timedelta(minutes=minutes)
