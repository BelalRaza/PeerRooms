import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from peerrooms.api.errors import handle_peerrooms_error
from peerrooms.api.routes import connections, discover, notifications, rooms, students
from peerrooms.app.bootstrap import build_app
from peerrooms.domain.exceptions import PeerRoomsError
from seed import seed


@asynccontextmanager
async def lifespan(api: FastAPI) -> AsyncIterator[None]:
    application = build_app()
    if os.environ.get("PEERROOMS_SEED") == "1":
        seed(application)
    api.state.peerrooms = application
    yield


def create_app() -> FastAPI:
    api = FastAPI(
        title="PeerRooms API", version="0.1.0", lifespan=lifespan, docs_url=None, redoc_url=None,
        description="Register or sign in, then Authorize with the returned student ID.",
    )
    api.add_exception_handler(PeerRoomsError, handle_peerrooms_error)
    for router in (students.router, rooms.router, discover.router, connections.router, notifications.router):
        api.include_router(router, prefix="/api")

    @api.get("/docs", include_in_schema=False)
    def swagger() -> HTMLResponse:
        return get_swagger_ui_html(
            openapi_url="./openapi.json", title="PeerRooms API · Swagger UI",
            swagger_js_url="./_swagger/swagger-ui-bundle.js",
            swagger_css_url="./_swagger/swagger-ui.css",
            swagger_favicon_url="./_swagger/favicon-32x32.png",
        )

    api.mount(
        "/_swagger", StaticFiles(directory=Path(__file__).with_name("swagger")), name="swagger-assets",
    )
    api.mount("/", StaticFiles(directory=Path(__file__).resolve().parents[2] / "web", html=True), name="web")
    return api


app = create_app()
