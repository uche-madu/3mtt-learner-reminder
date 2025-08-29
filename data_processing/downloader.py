# data_processing/downloader.py
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

from config import settings
from log import logger
from utils.retry import is_transient_error, log_before_retry


@retry(
    stop=stop_after_attempt(settings.max_retries),
    wait=wait_exponential(multiplier=settings.retry_delay, min=1, max=60),
    retry=retry_if_exception(is_transient_error),
    before_sleep=log_before_retry,
    reraise=True,
)
async def get_bearer_token() -> str:
    """Retrieve a Bearer token from Darey API asynchronously, with retries on transient errors."""
    url = "https://aiservice.academy.darey.io/ai/api/token"
    headers = {
        "x-business-id": settings.business_id.get_secret_value(),
        "Accept": "application/json",
    }
    payload = {
        "username": settings.darey_username.get_secret_value(),
        "password": settings.darey_password.get_secret_value(),
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            token = response.json()["data"]["access_token"]
            logger.info("Successfully obtained bearer token")
            return token
        except Exception as e:
            logger.error(f"Failed to get bearer token: {e}")
            raise


@retry(
    stop=stop_after_attempt(settings.max_retries),
    wait=wait_exponential(multiplier=settings.retry_delay, min=1, max=60),
    retry=retry_if_exception(is_transient_error),
    before_sleep=log_before_retry,
    reraise=True,
)
async def stream_learners(page_size: int | None = None):
    """
    Async generator that yields learners from Darey API in pages.
    Implements retry on transient errors per request.
    """
    page = 1
    limit = page_size or settings.download_limit
    token = await get_bearer_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "x-business-id": settings.business_id.get_secret_value(),
        "Accept": "application/json",
    }

    async with httpx.AsyncClient(timeout=None) as client:
        while True:
            url = f"{settings.download_url}?page={page}&limit={limit}"
            try:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()
                learners = data.get("data", {}).get("info", [])
                if not learners:
                    logger.info(f"No more learners found on page {page}. Stopping.")
                    break
                for learner in learners:
                    yield learner
                logger.info(f"Yielded {len(learners)} learners from page {page}")
                page += 1
            except Exception as e:
                if is_transient_error(e):
                    # let tenacity handle retry
                    raise
                logger.error(f"Failed to fetch learners on page {page}: {e}")
                break
