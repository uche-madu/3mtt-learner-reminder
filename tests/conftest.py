import pytest
from config import settings as app_settings


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
