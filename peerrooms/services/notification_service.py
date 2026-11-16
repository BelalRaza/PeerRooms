from collections.abc import Callable

from peerrooms.domain import events
from peerrooms.domain.enums import NotificationType
from peerrooms.domain.exceptions import PermissionDeniedError
from peerrooms.domain.notification import Notification
from peerrooms.ports.clock import Clock
from peerrooms.ports.events import EventListener
from peerrooms.ports.repositories import NotificationRepository, RoomRepository, StudentRepository


class NotificationService(EventListener):
    """Turn events into readable inbox items without coupling publishers to delivery."""

    def __init__(
        self, inbox: NotificationRepository, students: StudentRepository, rooms: RoomRepository,
        clock: Clock, ids: Callable[[], str],
    ) -> None:
        self._inbox, self._students, self._rooms = inbox, students, rooms
        self._clock, self._ids = clock, ids

    def handle(self, event: object) -> None:
        match event:
            case events.StudentJoined(room_id, student_id, host_id):
                self._notify(host_id, NotificationType.STUDENT_JOINED,
                             f"{self._name(student_id)} joined {self._topic(room_id)}.")
            case events.StudentWaitlisted(room_id, student_id, host_id):
                self._notify(host_id, NotificationType.STUDENT_WAITLISTED,
                             f"{self._name(student_id)} joined the waitlist for {self._topic(room_id)}.")
            case events.StudentPromoted(room_id, student_id):
                self._notify(student_id, NotificationType.STUDENT_PROMOTED,
                             f"You have a seat in {self._topic(room_id)}.")
            case events.HostChanged(room_id, new_host_id):
                self._notify(new_host_id, NotificationType.HOST_CHANGED,
                             f"You are now the host of {self._topic(room_id)}.")
            case events.MemberRemoved(room_id, student_id):
                self._notify(student_id, NotificationType.MEMBER_REMOVED,
                             f"The host removed you from {self._topic(room_id)}.")
            case events.RoomClosed(room_id, recipient_ids) if recipient_ids:
                text = f"{self._topic(room_id)} has closed."
                for student_id in recipient_ids:
                    self._notify(student_id, NotificationType.ROOM_CLOSED, text)
            case events.ConnectionRequested(_, sender_id, receiver_id):
                self._notify(receiver_id, NotificationType.CONNECTION_REQUESTED,
                             f"{self._name(sender_id)} sent you a connection request.")
            case events.ConnectionAccepted(_, sender_id, receiver_id):
                self._notify(sender_id, NotificationType.CONNECTION_ACCEPTED,
                             f"{self._name(receiver_id)} accepted your connection request.")

    def inbox(self, student_id: str) -> list[Notification]:
        self._students.get(student_id)
        return sorted(
            self._inbox.for_student(student_id),
            key=lambda item: (item.created_at, item.id), reverse=True,
        )

    def mark_read(self, notification_id: str, by_id: str) -> None:
        self._students.get(by_id)
        item = self._inbox.get(notification_id)
        if item.recipient_id != by_id:
            raise PermissionDeniedError("Only the recipient can mark this notification as read.")
        item.mark_read()
        self._inbox.save(item)

    def _notify(self, recipient_id: str, kind: NotificationType, text: str) -> None:
        self._inbox.save(Notification(self._ids(), recipient_id, kind, text, self._clock.now()))

    def _name(self, student_id: str) -> str:
        return self._students.get(student_id).name

    def _topic(self, room_id: str) -> str:
        return self._rooms.get(room_id).topic
