import os
import tempfile
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

API_KEY = "test-key"
os.environ["API_KEY"] = API_KEY
os.environ["DATABASE_PATH"] = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["SEED_ON_STARTUP"] = "false"

from app.main import app  # noqa: E402

FUTURE = "2099-12-10T09:{minute}:00Z"


def make_slots(
    count: int = 3, provider: str = "Dr Chioma Okafor"
) -> list[dict[str, str]]:
    return [
        {
            "id": f"s{i}",
            "provider": provider,
            "start": f"2099-12-10T{9 + i:02d}:00:00Z",
            "end": f"2099-12-10T{9 + i:02d}:30:00Z",
        }
        for i in range(1, count + 1)
    ]


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app, headers={"X-API-Key": API_KEY}) as test_client:
        response = test_client.post("/reset", json={"slots": make_slots()})
        assert response.status_code == 200
        yield test_client
