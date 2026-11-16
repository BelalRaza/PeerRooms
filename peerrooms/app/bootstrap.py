from threading import Lock

from peerrooms.app.facade import PeerRoomsApp
from peerrooms.domain import events
from peerrooms.factories.room_factory import RoomFactory
from peerrooms.infrastructure.clocks import SystemClock
from peerrooms.infrastructure.event_bus import EventBus
from peerrooms.infrastructure.ids import new_id
from peerrooms.infrastructure.in_memory_repositories import (
    InMemoryConnectionRepository, InMemoryConnectionRequestRepository,
    InMemoryNotificationRepository, InMemoryRoomRepository, InMemoryStudentRepository,
)
from peerrooms.ports.clock import Clock
from peerrooms.services.connection_service import ConnectionService
from peerrooms.services.discovery_service import DiscoveryService
from peerrooms.services.notification_service import NotificationService
from peerrooms.services.room_service import RoomService
from peerrooms.services.student_service import StudentService
from peerrooms.strategies.matching import JaccardInterestStrategy, SharedRoomsStrategy, WeightedStrategy


def build_app(clock: Clock | None = None) -> PeerRoomsApp:
    time = clock if clock is not None else SystemClock()
    students, rooms = InMemoryStudentRepository(), InMemoryRoomRepository()
    requests, connections = InMemoryConnectionRequestRepository(), InMemoryConnectionRepository()
    notifications = InMemoryNotificationRepository()
    bus = EventBus()
    writes = Lock()

    inbox = NotificationService(notifications, students, rooms, time, new_id)
    for event_type in (
        events.RoomCreated, events.StudentJoined, events.StudentWaitlisted, events.StudentLeft,
        events.StudentPromoted, events.HostChanged, events.MemberRemoved, events.RoomClosed,
        events.MessagePosted, events.ConnectionRequested, events.ConnectionAccepted,
    ):
        bus.subscribe(event_type, inbox)

    jaccard = JaccardInterestStrategy()
    weighted = WeightedStrategy([(jaccard, 0.7), (SharedRoomsStrategy(rooms), 0.3)])

    return PeerRoomsApp(
        StudentService(students, new_id, writes),
        RoomService(rooms, students, RoomFactory(new_id), bus, time),
        ConnectionService(students, requests, connections, bus, time, new_id, writes),
        DiscoveryService(students, rooms, connections, requests, weighted, writes),
        inbox,
        {"jaccard": jaccard, "weighted": weighted},
    )
