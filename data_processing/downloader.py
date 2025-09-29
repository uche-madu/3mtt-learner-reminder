# data_processing/downloader.py
from typing import AsyncGenerator
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
    url = "https://aiservice.academy.dareyio.com/ai/api/token"
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
async def stream_learners(batch_size: int = 500) -> AsyncGenerator[dict, None]:
    """
    Async generator that yields learners from Darey API in batches.
    Since the endpoint isn't truly paginated, fetch all at once
    and yield learners in streaming batches.
    """
    token = await get_bearer_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "x-business-id": settings.business_id.get_secret_value(),
        "Accept": "application/json",
    }

    url = f"{settings.download_url}?page=1&limit={settings.download_limit}"
    async with httpx.AsyncClient(timeout=None) as client:
        try:
            logger.info(f"Fetching all learners from {url}")
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            learners = data.get("data", {}).get("info", [])

            logger.info(f"Retrieved {len(learners)} total learners")

            # Yield in batches instead of one giant list
            for i in range(0, len(learners), batch_size):
                batch = learners[i : i + batch_size]
                logger.info(
                    f"Yielding batch of {len(batch)} learners ({i + 1}-{i + len(batch)})"
                )
                for learner in batch:
                    yield learner
        except Exception as e:
            if is_transient_error(e):
                # let tenacity handle retry
                raise
            logger.error(f"Failed to fetch learners: {e}")
