from fastapi import APIRouter, Response

from peerrooms.api.deps import App, StudentId
from peerrooms.api.schemas import InterestsRequest, RegisterRequest, SignInRequest, StudentResponse
from peerrooms.app.views import StudentView

router = APIRouter(tags=["Students"])


@router.post("/students", response_model=StudentResponse, status_code=201)
def register(data: RegisterRequest, app: App) -> StudentView:
    return app.register(data.name, data.email, data.department, data.year, data.interests)


@router.post("/sessions", response_model=StudentResponse)
def sign_in(data: SignInRequest, app: App) -> StudentView:
    return app.sign_in(data.email)


@router.get("/students/me", response_model=StudentResponse)
def profile(student_id: StudentId, app: App) -> StudentView:
    return app.profile(student_id)


@router.put("/students/me/interests", response_model=StudentResponse)
def update_interests(data: InterestsRequest, student_id: StudentId, app: App) -> StudentView:
    return app.update_interests(student_id, data.interests)


@router.post("/students/me/blocks/{other_id}", status_code=204, response_class=Response)
def block_student(other_id: str, student_id: StudentId, app: App) -> None:
    app.block_student(student_id, other_id)
