import pytest

from tests.helpers import quick_room, register
from peerrooms.app.facade import PeerRoomsApp
from peerrooms.domain.exceptions import ValidationError
from peerrooms.infrastructure.clocks import FakeClock


def test_discover_filters_network_pending_self_and_zero_scores(application: PeerRoomsApp) -> None:
    me = register(application, "Me", "AI", "Python")
    linked, pending_out, pending_in, zelda, anna = (
        register(application, name, "AI") for name in ["Linked", "Sent", "Received", "Zelda", "Anna"]
    )
    register(application, "No overlap", "art")
    application.accept(linked.id, application.send_request(me.id, linked.id).id)
    application.send_request(me.id, pending_out.id)
    application.send_request(pending_in.id, me.id)
    assert [peer.student for peer in application.suggest_peers(me.id, strategy="jaccard")] == [anna, zelda]
    assert [peer.student for peer in application.suggest_peers(me.id, limit=1)] == [anna]
    empty = register(application, "Empty", "dancing")
    assert application.suggest_peers(empty.id) == []
    with pytest.raises(ValidationError):
        application.suggest_peers(me.id, limit=0)
    with pytest.raises(ValidationError):
        application.suggest_peers(me.id, strategy="typo")


def test_recommendation_score_then_seat_then_recency(application: PeerRoomsApp, clock: FakeClock) -> None:
    me = register(application, "Me", "ai")
    host = register(application, "Host")
    guest = register(application, "Guest")
    open_old = quick_room(application, host.id, "Old", 2)
    clock.advance(1)
    full_new = quick_room(application, host.id, "Full", 2)
    application.join_room(guest.id, full_new.id)
    clock.advance(1)
    open_new = quick_room(application, host.id, "New", 2)
    open_low = quick_room(application, host.id, "Design", 2, ("design",))
    closed = quick_room(application, host.id, "Closed", 2)
    application.close_room(host.id, closed.id)
    assert [room.id for room in application.recommend_rooms(me.id)] == [
        open_new.id, open_old.id, full_new.id, open_low.id,
    ]
    application.join_room(me.id, full_new.id)
    application.join_room(me.id, open_old.id)
    application.update_interests(me.id, ["design"])
    assert [room.id for room in application.recommend_rooms(me.id)] == [open_low.id, open_new.id]
