from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from peerrooms.api.deps import get_app
from peerrooms.api.main import create_app
from peerrooms.app.facade import PeerRoomsApp


@pytest.fixture
def client(application: PeerRoomsApp, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.delenv("PEERROOMS_SEED", raising=False)
    api = create_app()
    api.dependency_overrides[get_app] = lambda: application
    with TestClient(api) as test_client:
        yield test_client
