import pytest
import types
from data_processing import downloader


@pytest.mark.asyncio
async def test_stream_learners_single_page(monkeypatch):
    """Test stream_learners yields all learners for a single page."""

    learners_data = [{"_id": "1"}, {"_id": "2"}]

    async def mock_get(*args, **kwargs):
        class MockResp:
            def raise_for_status(self):
                return None

            def json(self):
                return {"data": {"info": learners_data}}

        return MockResp()

    class MockClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def get(self, *args, **kwargs):
            return await mock_get(*args, **kwargs)

    async def mock_get_bearer_token() -> str:
        return "mock_token"

    # patch both client and bearer_token
    monkeypatch.setattr(
        downloader,
        "httpx",
        types.SimpleNamespace(AsyncClient=lambda *a, **k: MockClient()),
    )
    monkeypatch.setattr(downloader, "get_bearer_token", mock_get_bearer_token)

    results = []
    async for learner in downloader.stream_learners(page_size=10):
        results.append(learner)

    assert results == learners_data


@pytest.mark.asyncio
async def test_stream_learners_empty(monkeypatch):
    """Test generator stops when no learners are returned."""

    async def mock_get(*args, **kwargs):
        class MockResp:
            def raise_for_status(self):
                return None

            def json(self):
                return {"data": {"info": []}}

        return MockResp()

    class MockClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def get(self, *args, **kwargs):
            return await mock_get(*args, **kwargs)

    async def mock_get_bearer_token() -> str:
        return "mock_token"

    monkeypatch.setattr(
        downloader,
        "httpx",
        types.SimpleNamespace(AsyncClient=lambda *a, **k: MockClient()),
    )
    monkeypatch.setattr(downloader, "get_bearer_token", mock_get_bearer_token)

    results = []
    async for learner in downloader.stream_learners(page_size=10):
        results.append(learner)

    assert results == []


@pytest.mark.asyncio
async def test_stream_learners_pagination(monkeypatch):
    """Test multiple pages are yielded correctly."""

    pages = [[{"_id": "1"}, {"_id": "2"}], [{"_id": "3"}], []]
    call_count = {"count": 0}

    async def mock_get(*args, **kwargs):
        class MockResp:
            def raise_for_status(self):
                return None

            def json(self):
                data = {"data": {"info": pages[call_count["count"]]}}
                call_count["count"] += 1
                return data

        return MockResp()

    class MockClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def get(self, *args, **kwargs):
            return await mock_get(*args, **kwargs)

    async def mock_get_bearer_token() -> str:
        return "mock_token"

    monkeypatch.setattr(
        downloader,
        "httpx",
        types.SimpleNamespace(AsyncClient=lambda *a, **k: MockClient()),
    )
    monkeypatch.setattr(downloader, "get_bearer_token", mock_get_bearer_token)

    results = []
    async for learner in downloader.stream_learners(page_size=2):
        results.append(learner["_id"])

    assert results == ["1", "2", "3"]
