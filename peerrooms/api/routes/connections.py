from fastapi import APIRouter

from peerrooms.api.deps import App, StudentId
from peerrooms.api.schemas import (
    ConnectionRequestResponse, ConnectionResponse, PendingRequestsResponse,
    SendConnectionRequest, StudentResponse,
)
from peerrooms.app.views import ConnectionView, PendingRequestsView, RequestView, StudentView

router = APIRouter(prefix="/connections", tags=["Connections"])


@router.post("/requests", response_model=ConnectionRequestResponse, status_code=201)
def send_request(data: SendConnectionRequest, student_id: StudentId, app: App) -> RequestView:
    return app.send_request(student_id, data.receiver_id)


@router.post("/requests/{request_id}/accept", response_model=ConnectionResponse)
def accept(request_id: str, student_id: StudentId, app: App) -> ConnectionView:
    return app.accept(student_id, request_id)


@router.post("/requests/{request_id}/reject", response_model=ConnectionRequestResponse)
def reject(request_id: str, student_id: StudentId, app: App) -> RequestView:
    return app.reject(student_id, request_id)


@router.post("/requests/{request_id}/cancel", response_model=ConnectionRequestResponse)
def cancel(request_id: str, student_id: StudentId, app: App) -> RequestView:
    return app.cancel(student_id, request_id)


@router.get("/requests", response_model=PendingRequestsResponse)
def pending_requests(student_id: StudentId, app: App) -> PendingRequestsView:
    return app.pending_requests(student_id)


@router.get("", response_model=list[StudentResponse])
def network_of(student_id: StudentId, app: App) -> list[StudentView]:
    return app.network_of(student_id)
