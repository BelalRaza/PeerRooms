from fastapi import APIRouter

from peerrooms.api.deps import App, StudentId
from peerrooms.api.schemas import PeerResponse
from peerrooms.app.views import PeerView

router = APIRouter(prefix="/discover", tags=["Discover"])


@router.get("/peers", response_model=list[PeerResponse])
def suggest_peers(
    student_id: StudentId, app: App, limit: int = 10, strategy: str | None = None,
) -> list[PeerView]:
    return app.suggest_peers(student_id, limit, strategy)
