from fastapi import Request
from fastapi.responses import JSONResponse

from peerrooms.domain.exceptions import (
    ConflictError, NotFoundError, PeerRoomsError, PermissionDeniedError, RoomError, ValidationError,
)

ERROR_STATUS: dict[type[PeerRoomsError], int] = {
    ValidationError: 400,
    NotFoundError: 404,
    PermissionDeniedError: 403,
    ConflictError: 409,
    RoomError: 409,
}


def handle_peerrooms_error(_: Request, exc: PeerRoomsError) -> JSONResponse:
    for group in type(exc).__mro__:
        if group in ERROR_STATUS:
            return JSONResponse(
                {"error": type(exc).__name__, "message": str(exc)}, status_code=ERROR_STATUS[group],
            )
    return JSONResponse(
        {"error": type(exc).__name__, "message": str(exc)}, status_code=400,
    )
