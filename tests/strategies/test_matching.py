import pytest

from tests.helpers import NOW, quick_room, register, student
from peerrooms.app.facade import PeerRoomsApp
from peerrooms.domain.exceptions import ValidationError
from peerrooms.domain.room import Room
from peerrooms.infrastructure.in_memory_repositories import InMemoryRoomRepository
from peerrooms.strategies.matching import JaccardInterestStrategy, SharedRoomsStrategy, WeightedStrategy, jaccard
from seed import seed


def test_jaccard_and_weight_contract() -> None:
    strategy = JaccardInterestStrategy()
    aman, riya = student("Aman", "python", "ai", "startups", "football"), student("Riya", "ai", "startups", "design")
    assert strategy.score(aman, riya) == pytest.approx(0.4)
    assert jaccard(frozenset(), frozenset()) == 0
    for weights in ((0.5, 0.4), (-1, 2), (float("nan"), 1)):
        with pytest.raises(ValidationError):
            WeightedStrategy([(strategy, weight) for weight in weights])


def test_shared_room_score_caps_at_five(room: Room) -> None:
    history = InMemoryRoomRepository()
    room.join("A", NOW)
    room.close("H")
    for index in range(6):
        room.id = str(index)
        history.save(room)
    assert SharedRoomsStrategy(history).score(student("A"), student("H")) == 1.0


def test_dry_run_rankings_and_exact_scores(application: PeerRoomsApp) -> None:
    seed(application)
    aman = application.sign_in("aman@college.edu")
    a_room = quick_room(application, aman.id)
    for name in ("riya", "kabir", "dev", "isha"):
        application.join_room(application.sign_in(name + "@college.edu").id, a_room.id)
    application.leave_room(application.sign_in("riya@college.edu").id, a_room.id)
    application.leave_room(aman.id, a_room.id)

    weighted = application.suggest_peers(aman.id, strategy="weighted")
    jaccard_only = application.suggest_peers(aman.id, strategy="jaccard")
    assert [item.student.name for item in weighted] == ["Dev", "Kabir", "Riya", "Isha"]
    assert [item.score for item in weighted] == pytest.approx([0.41, 0.355, 0.34, 0.20])
    assert [item.student.name for item in jaccard_only] == ["Dev", "Riya", "Kabir", "Isha"]
    assert [item.score for item in jaccard_only] == pytest.approx([0.50, 0.40, 0.25, 0.20])
    assert application.suggest_peers(aman.id) == weighted
