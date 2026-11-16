import pytest

from tests.helpers import NOW
from peerrooms.domain.enums import NotificationType
from peerrooms.domain.exceptions import NotificationNotFoundError
from peerrooms.domain.notification import Notification
from peerrooms.infrastructure.in_memory_repositories import InMemoryNotificationRepository


def test_inbox_snapshot_and_recipient_filter() -> None:
    repo = InMemoryNotificationRepository()
    item = Notification("n", "A", NotificationType.ROOM_CLOSED, "Closed.", NOW)
    repo.save(item)
    item.mark_read()
    assert not repo.get("n").is_read and not repo.for_student("B")
    repo.save(item)
    assert [notification.id for notification in repo.for_student("A") if notification.is_read] == ["n"]
    with pytest.raises(NotificationNotFoundError):
        repo.get("missing")
