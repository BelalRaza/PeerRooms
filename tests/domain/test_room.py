from datetime import timedelta

import pytest

from tests.helpers import NOW
from peerrooms.domain.enums import JoinResult, RoomRole, RoomStatus
from peerrooms.domain.exceptions import (
    AlreadyInRoomError, NotAMemberError, PermissionDeniedError, RoomClosedError, ValidationError,
)
from peerrooms.domain.room import LeaveResult, Room


def test_capacity_three_dry_run(room: Room) -> None:
    def check(seats: str, waitlist: str, status: RoomStatus, host: str | None) -> None:
        assert [member.student_id for member in room.members] == seats.split()
        assert room.waitlist == tuple(waitlist.split())
        assert room.status() is status and room.host_id == host
        assert [member.student_id for member in room.members if member.role is RoomRole.HOST] == (
            [host] if host else []
        )

    check("H", "", RoomStatus.OPEN, "H")
    assert room.join("S1", NOW + timedelta(minutes=1)).result is JoinResult.JOINED
    check("H S1", "", RoomStatus.OPEN, "H")
    room.join("S2", NOW + timedelta(minutes=2))
    check("H S1 S2", "", RoomStatus.FULL, "H")
    third = room.join("S3", NOW + timedelta(minutes=3))
    assert (third.result, third.position) == (JoinResult.WAITLISTED, 1)
    check("H S1 S2", "S3", RoomStatus.FULL, "H")
    assert room.join("S4", NOW + timedelta(minutes=4)).position == 2
    check("H S1 S2", "S3 S4", RoomStatus.FULL, "H")
    assert room.leave("S1", NOW + timedelta(minutes=5)) == LeaveResult(promoted_id="S3")
    check("H S2 S3", "S4", RoomStatus.FULL, "H")
    assert room.members[-1].joined_at == NOW + timedelta(minutes=5)
    assert room.leave("H", NOW + timedelta(minutes=6)) == LeaveResult("S4", "S2")
    check("S2 S3 S4", "", RoomStatus.FULL, "S2")
    assert room.leave("S3", NOW + timedelta(minutes=7)) == LeaveResult()
    check("S2 S4", "", RoomStatus.OPEN, "S2")
    assert room.leave("S2", NOW + timedelta(minutes=8)) == LeaveResult(new_host_id="S4")
    check("S4", "", RoomStatus.OPEN, "S4")
    assert room.leave("S4", NOW + timedelta(minutes=9)) == LeaveResult(closed=True)
    check("", "", RoomStatus.CLOSED, None)
    assert room.past_participants == {"H", "S1", "S2", "S3", "S4"}


def test_duplicate_and_waitlist_departure(room: Room) -> None:
    for identifier in ["A", "B", "C", "D"]:
        room.join(identifier, NOW)
    for identifier in ["H", "C"]:
        with pytest.raises(AlreadyInRoomError):
            room.join(identifier, NOW)
    assert room.leave("C", NOW) == LeaveResult()
    assert room.waitlist == ("D",) and room.status() is RoomStatus.FULL
    assert "C" not in room.past_participants
    assert room.leave("H", NOW) == LeaveResult("D", "A")
    assert room.status() is RoomStatus.FULL


def test_chat_requires_seat_and_valid_length(room: Room) -> None:
    for identifier in ["A", "B", "C"]:
        room.join(identifier, NOW)
    for identifier in ["C", "D"]:
        with pytest.raises(NotAMemberError):
            room.post_message(identifier, "hello", NOW)
    for invalid in ["", "   ", "a" * 1001, "a" * 1000 + " "]:
        with pytest.raises(ValidationError):
            room.post_message("H", invalid, NOW)
    assert room.post_message("H", "a" * 1000, NOW).content == "a" * 1000


def test_host_permissions_and_closed_terminal_state(room: Room) -> None:
    for identifier in ["A", "B", "C"]:
        room.join(identifier, NOW)
    with pytest.raises(PermissionDeniedError):
        room.close("A")
    with pytest.raises(PermissionDeniedError):
        room.remove_member("A", "B", NOW)
    with pytest.raises(ValidationError):
        room.remove_member("H", "H", NOW)
    with pytest.raises(NotAMemberError):
        room.remove_member("H", "C", NOW)
    with pytest.raises(NotAMemberError):
        room.leave("unknown", NOW)
    assert room.remove_member("H", "B", NOW).promoted_id == "C"
    room.join("D", NOW)
    room.post_message("H", "hello", NOW)
    room.close("H")
    assert not room.members and not room.waitlist and room.host_id is None
    assert [message.content for message in room.messages] == ["hello"]
    for action in (lambda: room.close("H"), lambda: room.join("A", NOW),
                   lambda: room.leave("A", NOW), lambda: room.post_message("A", "hello", NOW)):
        with pytest.raises(RoomClosedError):
            action()
