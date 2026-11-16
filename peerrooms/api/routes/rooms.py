from fastapi import APIRouter, Response

from peerrooms.api.deps import App, StudentId
from peerrooms.api.schemas import (
    CreateRoomRequest, JoinResponse, LeaveResponse, MessageResponse,
    PostMessageRequest, RoomCardResponse, RoomDetailResponse,
)
from peerrooms.app.views import JoinView, LeaveView, MessageView, RoomCardView, RoomDetailView
from peerrooms.domain.enums import RoomStatus

router = APIRouter(prefix="/rooms", tags=["Rooms"])


@router.get("", response_model=list[RoomCardResponse])
def list_rooms(
    student_id: StudentId, app: App, tag: str | None = None, status: RoomStatus | None = None,
) -> list[RoomCardView]:
    return app.list_rooms(student_id, tag, status)


@router.get("/recommended", response_model=list[RoomCardResponse])
def recommend_rooms(student_id: StudentId, app: App, limit: int = 10) -> list[RoomCardView]:
    return app.recommend_rooms(student_id, limit)


@router.post("", response_model=RoomCardResponse, status_code=201)
def create_room(data: CreateRoomRequest, student_id: StudentId, app: App) -> RoomCardView:
    return app.create_room(student_id, data.room_type, data.topic, data.prompt, data.tags, data.capacity)


@router.get("/{room_id}", response_model=RoomDetailResponse)
def room_detail(room_id: str, student_id: StudentId, app: App) -> RoomDetailView:
    return app.room_detail(student_id, room_id)


@router.post("/{room_id}/join", response_model=JoinResponse)
def join_room(room_id: str, student_id: StudentId, app: App) -> JoinView:
    return app.join_room(student_id, room_id)


@router.post("/{room_id}/leave", response_model=LeaveResponse)
def leave_room(room_id: str, student_id: StudentId, app: App) -> LeaveView:
    return app.leave_room(student_id, room_id)


@router.delete("/{room_id}/members/{target_id}", status_code=204, response_class=Response)
def remove_member(room_id: str, target_id: str, student_id: StudentId, app: App) -> None:
    app.remove_member(student_id, room_id, target_id)


@router.post("/{room_id}/close", status_code=204, response_class=Response)
def close_room(room_id: str, student_id: StudentId, app: App) -> None:
    app.close_room(student_id, room_id)


@router.post("/{room_id}/messages", response_model=MessageResponse, status_code=201)
def post_message(room_id: str, data: PostMessageRequest, student_id: StudentId, app: App) -> MessageView:
    return app.post_message(student_id, room_id, data.content)
