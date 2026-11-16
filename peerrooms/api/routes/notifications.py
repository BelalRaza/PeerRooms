from fastapi import APIRouter, Response

from peerrooms.api.deps import App, StudentId
from peerrooms.api.schemas import NotificationResponse
from peerrooms.app.views import NotificationView

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=list[NotificationResponse])
def inbox(student_id: StudentId, app: App) -> list[NotificationView]:
    return app.inbox(student_id)


@router.post("/{notification_id}/read", status_code=204, response_class=Response)
def mark_read(notification_id: str, student_id: StudentId, app: App) -> None:
    app.mark_read(student_id, notification_id)
