import pytest
import pytest_asyncio
from datetime import datetime, timedelta, timezone

from config import settings as app_settings

now = datetime.now(timezone.utc)


@pytest.fixture
def settings():
    """Override settings for tests."""
    return app_settings


@pytest.fixture
def mock_get_bearer_token(monkeypatch):
    """Fixture to mock get_bearer_token to always return a fixed token."""
    monkeypatch.setattr(
        "data_processing.downloader.get_bearer_token", lambda: "mock_token"
    )
    return "mock_token"


@pytest.fixture
def mock_async_client(monkeypatch):
    """Fixture to mock httpx.AsyncClient for all async requests."""

    class MockResp:
        def __init__(self, json_data=None):
            self._json_data = json_data or {}

        def raise_for_status(self):
            return None

        def json(self):
            return self._json_data

    class MockClient:
        def __init__(self, responses=None):
            self.responses = responses or []
            self.call_count = 0

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def get(self, *args, **kwargs):
            resp = (
                self.responses[self.call_count]
                if self.call_count < len(self.responses)
                else MockResp()
            )
            self.call_count += 1
            return resp

        async def post(self, *args, **kwargs):
            resp = (
                self.responses[self.call_count]
                if self.call_count < len(self.responses)
                else MockResp()
            )
            self.call_count += 1
            return resp

    monkeypatch.setattr(
        "data_processing.downloader.httpx.AsyncClient",
        lambda *args, **kwargs: MockClient(),
    )
    return MockClient


@pytest_asyncio.fixture
async def learners() -> list[dict]:
    """
    Fixture providing learners with varied data for classification tests.
    Covers inactive, low-score, completed, and invalid cases.
    """
    return [
        # Inactive learner (>40 days)
        {
            "_id": "1",
            "email": "inactive@test.com",
            "last_loggedin_date": (now - timedelta(days=40)).isoformat(),
            "program_data": {"progress_status": 80},
        },
        # Low-score learner (recent login, low progress)
        {
            "_id": "2",
            "email": "low@test.com",
            "last_loggedin_date": (now - timedelta(days=1)).isoformat(),
            "program_data": {"progress_status": 10},
        },
        # Completed learner (should be skipped)
        {
            "_id": "3",
            "email": "completed@test.com",
            "last_loggedin_date": (now - timedelta(days=1)).isoformat(),
            "program_data": {"progress_status": 100},
        },
        # Inactive + low score → should be classified as inactive only
        {
            "_id": "4",
            "email": "conflict@test.com",
            "last_loggedin_date": (now - timedelta(days=40)).isoformat(),
            "program_data": {"progress_status": 10},
        },
        # Missing email → should be skipped
        {
            "_id": "5",
            "email": None,
            "last_loggedin_date": (now - timedelta(days=1)).isoformat(),
            "program_data": {"progress_status": 10},
        },
        # Missing _id → should be skipped
        {
            "_id": None,
            "email": "noid@test.com",
            "last_loggedin_date": (now - timedelta(days=1)).isoformat(),
            "program_data": {"progress_status": 20},
        },
    ]
