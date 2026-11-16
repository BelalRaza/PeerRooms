from typing import Annotated

from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import APIKeyHeader

from peerrooms.app.facade import PeerRoomsApp

student_header = APIKeyHeader(
    name="X-Student-Id", scheme_name="Student identity", auto_error=False,
    description="Paste the id returned by POST /api/sessions or POST /api/students.",
)


def get_app(request: Request) -> PeerRoomsApp:
    return request.app.state.peerrooms


def current_student_id(student_id: Annotated[str | None, Security(student_header)]) -> str:
    if student_id is None or not student_id.strip():
        raise HTTPException(status_code=401, detail="Sign in to continue.")
    return student_id.strip()


App = Annotated[PeerRoomsApp, Depends(get_app)]
StudentId = Annotated[str, Depends(current_student_id)]
