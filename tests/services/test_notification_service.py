import pytest

from tests.helpers import quick_room, register
from peerrooms.app.facade import PeerRoomsApp
from peerrooms.domain.enums import NotificationType
from peerrooms.domain.exceptions import NotificationNotFoundError, PermissionDeniedError


def test_every_room_notification_type_has_the_intended_recipient(application: PeerRoomsApp) -> None:
    host, seated, first, second, third = map(
        lambda name: register(application, name), ("Host", "Seated", "First", "Second", "Third"),
    )
    room = quick_room(application, host.id, capacity=2)
    for student in (seated, first, second, third):
        application.join_room(student.id, room.id)
    assert [item.type for item in application.inbox(host.id)].count(NotificationType.STUDENT_JOINED) == 1
    assert [item.type for item in application.inbox(host.id)].count(NotificationType.STUDENT_WAITLISTED) == 3
    application.leave_room(host.id, room.id)
    application.remove_member(seated.id, room.id, first.id)
    assert {item.type for item in application.inbox(first.id)} == {
        NotificationType.STUDENT_PROMOTED, NotificationType.MEMBER_REMOVED,
    }
    assert [item.type for item in application.inbox(seated.id)] == [NotificationType.HOST_CHANGED]
    application.close_room(seated.id, room.id)
    assert {item.type for item in application.inbox(second.id)} == {
        NotificationType.STUDENT_PROMOTED, NotificationType.ROOM_CLOSED,
    }
    assert [item.type for item in application.inbox(third.id)] == [NotificationType.ROOM_CLOSED]
    assert "Campus AI" in application.inbox(third.id)[0].text


def test_connection_notifications_and_mark_read(application: PeerRoomsApp) -> None:
    sender, receiver = (register(application, name) for name in ("Sender", "Receiver"))
    sent = application.send_request(sender.id, receiver.id)
    requested, = application.inbox(receiver.id)
    assert not requested.is_read and requested.type is NotificationType.CONNECTION_REQUESTED
    with pytest.raises(PermissionDeniedError):
        application.mark_read(sender.id, requested.id)
    with pytest.raises(NotificationNotFoundError):
        application.mark_read(receiver.id, "missing")
    application.mark_read(receiver.id, requested.id)
    application.mark_read(receiver.id, requested.id)
    assert application.inbox(receiver.id)[0].is_read
    application.accept(receiver.id, sent.id)
    accepted, = application.inbox(sender.id)
    assert accepted.type is NotificationType.CONNECTION_ACCEPTED and "Receiver" in accepted.text
