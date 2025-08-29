# tests/integration/test_downloader_async.py
import pytest

from data_processing.downloader import stream_learners


@pytest.mark.asyncio
async def test_stream_learners_single_page(monkeypatch):
    """Test stream_learners yields all learners for a single page."""

    learners_data = [
        {"_id": "1", "email": "a@test.com"},
        {"_id": "2", "email": "b@test.com"},
    ]

    async def mock_get(*args, **kwargs):
        class MockResp:
            def raise_for_status(self):
                return None

            def json(self):
                return {"data": {"info": learners_data}}

        return MockResp()

    async def mock_get_empty(*args, **kwargs):
        class MockResp:
            def raise_for_status(self):
                return None

            def json(self):
                return {"data": {"info": []}}

        return MockResp()

    # Patch both AsyncClient and get_bearer_token
    async def mock_client(*args, **kwargs):
        class MockClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return None

            async def get(self, *args, **kwargs):
                return await mock_get(*args, **kwargs)

        return MockClient()

    monkeypatch.setattr("data_processing.downloader.httpx.AsyncClient", mock_client)
    monkeypatch.setattr(
        "data_processing.downloader.get_bearer_token", lambda: "mock_token"
    )

    results = []
    async for learner in stream_learners(page_size=10):
        results.append(learner)

    assert len(results) == len(learners_data)
    assert results[0]["_id"] == "1"
    assert results[1]["_id"] == "2"


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

    async def mock_client(*args, **kwargs):
        class MockClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return None

            async def get(self, *args, **kwargs):
                return await mock_get(*args, **kwargs)

        return MockClient()

    monkeypatch.setattr("data_processing.downloader.httpx.AsyncClient", mock_client)
    monkeypatch.setattr(
        "data_processing.downloader.get_bearer_token", lambda: "mock_token"
    )

    results = []
    async for learner in stream_learners(page_size=10):
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

    async def mock_client(*args, **kwargs):
        class MockClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return None

            async def get(self, *args, **kwargs):
                return await mock_get(*args, **kwargs)

        return MockClient()

    monkeypatch.setattr(
        "data_processing.downloader.httpx.AsyncClient",
        lambda *args, **kwargs: mock_client(),
    )
    monkeypatch.setattr(
        "data_processing.downloader.get_bearer_token", lambda: "mock_token"
    )

    results = []
    async for learner in stream_learners(page_size=2):
        results.append(learner["_id"])

    assert results == ["1", "2", "3"]
