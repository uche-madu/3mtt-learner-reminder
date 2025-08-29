# utils/retry.py
from tenacity import RetryCallState
from log import logger
import httpx

# --- Helper to identify transient exceptions ---
TRANSIENT_EXCEPTIONS = (
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
    httpx.NetworkError,
    httpx.HTTPStatusError,
)


def is_transient_error(exc: BaseException) -> bool:
    """Return True if exception is considered transient and worth retrying."""
    if isinstance(exc, httpx.HTTPStatusError):
        return 500 <= exc.response.status_code < 600
    return isinstance(exc, TRANSIENT_EXCEPTIONS)


def log_before_retry(retry_state: RetryCallState):
    """Log information before retrying."""
    exc = retry_state.outcome.exception() if retry_state.outcome is not None else None
    if exc is not None:
        logger.warning(
            f"Retrying due to transient error: {exc}. Attempt {retry_state.attempt_number}."
        )
    else:
        logger.warning(
            f"Retrying: attempt {retry_state.attempt_number} (no exception info)"
        )
