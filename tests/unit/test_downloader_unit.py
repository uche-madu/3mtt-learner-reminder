# tests/unit/test_downloader_unit.py
import pytest
import httpx

from data_processing import downloader


@pytest.mark.asyncio
async def test_get_bearer_token_success(mocker):
    """Should return token when Darey API responds successfully."""
    fake_response = mocker.Mock()
    fake_response.json.return_value = {"data": {"access_token": "fake-token"}}
    fake_response.raise_for_status.return_value = None

    mocker.patch(
        "httpx.AsyncClient.post",
        new_callable=mocker.AsyncMock,
        return_value=fake_response,
    )

    token = await downloader.get_bearer_token()
    assert token == "fake-token"
    fake_response.json.assert_called_once()


@pytest.mark.asyncio
async def test_get_bearer_token_failure(mocker):
    """Should raise if API request fails."""
    mock_error_response = mocker.Mock()
    mock_error_response.status_code = 400

    fake_response = mocker.Mock()
    fake_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "bad request", request=mocker.Mock(), response=mock_error_response
    )

    mocker.patch(
        "httpx.AsyncClient.post",
        new_callable=mocker.AsyncMock,
        return_value=fake_response,
    )

    with pytest.raises(httpx.HTTPStatusError):
        await downloader.get_bearer_token()


@pytest.mark.asyncio
async def test_stream_learners_single_page(mocker):
    """Should yield learners from a single page and stop."""
    learners = [{"_id": "1"}, {"_id": "2"}]

    # Page 1 with learners
    resp1 = mocker.Mock()
    resp1.json.return_value = {"data": {"info": learners}}
    resp1.raise_for_status.return_value = None

    # Page 2 with no learners → stops loop
    resp2 = mocker.Mock()
    resp2.json.return_value = {"data": {"info": []}}
    resp2.raise_for_status.return_value = None

    responses = [resp1, resp2]

    async def fake_get(url, headers):
        return responses.pop(0)

    mocker.patch(
        "data_processing.downloader.get_bearer_token", return_value="fake-token"
    )
    mocker.patch(
        "httpx.AsyncClient.get", new_callable=mocker.AsyncMock, side_effect=fake_get
    )

    results = []
    async for learner in downloader.stream_learners(page_size=2):
        results.append(learner)

    assert results == learners


@pytest.mark.asyncio
async def test_stream_learners_multiple_pages(mocker):
    """Should iterate across multiple pages until no learners left."""
    page1 = [{"_id": "1"}]
    page2 = [{"_id": "2"}]

    resp1 = mocker.Mock()
    resp1.json.return_value = {"data": {"info": page1}}
    resp1.raise_for_status.return_value = None

    resp2 = mocker.Mock()
    resp2.json.return_value = {"data": {"info": page2}}
    resp2.raise_for_status.return_value = None

    resp3 = mocker.Mock()
    resp3.json.return_value = {"data": {"info": []}}
    resp3.raise_for_status.return_value = None

    responses = [resp1, resp2, resp3]

    async def fake_get(url, headers):
        return responses.pop(0)

    mocker.patch(
        "data_processing.downloader.get_bearer_token", return_value="fake-token"
    )
    mocker.patch(
        "httpx.AsyncClient.get",
        new_callable=mocker.AsyncMock,
        side_effect=fake_get,
    )

    results = []
    async for learner in downloader.stream_learners(page_size=1):
        results.append(learner)

    assert results == [{"_id": "1"}, {"_id": "2"}]


@pytest.mark.asyncio
async def test_stream_learners_transient_error(mocker):
    """Should raise on transient error so tenacity can retry."""
    err = httpx.ConnectTimeout("timeout")

    async def fake_get(url, headers):
        raise err

    mocker.patch(
        "data_processing.downloader.get_bearer_token", return_value="fake-token"
    )
    mocker.patch(
        "httpx.AsyncClient.get",
        new_callable=mocker.AsyncMock,
        side_effect=fake_get,
    )
    mocker.patch("data_processing.downloader.is_transient_error", return_value=True)

    with pytest.raises(httpx.ConnectTimeout):
        results = []
        async for learner in downloader.stream_learners(page_size=1):
            results.append(learner)


@pytest.mark.asyncio
async def test_stream_learners_non_transient_error(mocker):
    """Should log and break on non-transient error without retry."""
    mock_error_response = mocker.Mock()
    mock_error_response.status_code = 400

    err = httpx.HTTPStatusError(
        "bad request", request=mocker.Mock(), response=mock_error_response
    )

    async def fake_get(url, headers):
        raise err

    mocker.patch(
        "data_processing.downloader.get_bearer_token", return_value="fake-token"
    )
    mocker.patch(
        "httpx.AsyncClient.get",
        new_callable=mocker.AsyncMock,
        side_effect=fake_get,
    )
    mocker.patch("data_processing.downloader.is_transient_error", return_value=False)

    results = []
    async for learner in downloader.stream_learners(page_size=1):
        results.append(learner)

    assert results == []
