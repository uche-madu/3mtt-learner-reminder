# data_processing/filters.py
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator, Any, Dict

from config import settings
from log import logger
from data_processing.downloader import stream_learners
from utils.batching import get_adaptive_batch_size

two_weeks_ago = datetime.now(timezone.utc) - timedelta(days=settings.inactive_days)

batch_size = get_adaptive_batch_size(
    min_batch=200, max_batch=500, target_memory_fraction=0.05
)


def filter_inactive(learner: Dict[str, Any]) -> bool:
    """
    Determine if a learner is inactive.

    Rules:
    - Learners missing `_id` or `email` are skipped (returns False).
    - Learners with progress_status == 100 (completed) are NOT considered inactive.
    - Learners with no `last_loggedin_date` are treated as inactive.
    - Learners with a last login older than settings.inactive_days are inactive.
    - Invalid date or invalid progress_status values are logged and the learner is skipped (returns False).
    """
    if not learner.get("_id") or not learner.get("email"):
        logger.warning(f"Skipping learner without _id or email: {learner.get('_id')}")
        return False

    # ---- completed learners are not inactive ----
    prog = learner.get("program_data", {}).get("progress_status")
    if prog is not None:
        try:
            # allow numeric or string values like "100"
            if float(prog) == 100.0:
                return False
        except Exception:
            # keep behavior conservative: log and continue (treat as non-completed)
            logger.warning(
                f"Invalid progress_status for learner {learner.get('_id')}: {prog}"
            )

    # ---- last login handling ----
    last_login = learner.get("last_loggedin_date")
    if not last_login:
        # No last login recorded -> treat as inactive
        return True

    try:
        # support ISO strings, convert Z -> +00:00
        last_login_dt = datetime.fromisoformat(last_login.replace("Z", "+00:00"))
    except Exception:
        logger.warning(
            f"Invalid last_loggedin_date for learner {learner.get('_id')}: {last_login}"
        )
        return False

    # compute cutoff at call time to avoid stale module-level value
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.inactive_days)
    return last_login_dt < cutoff


def filter_low_score(learner: dict) -> bool:
    """
    Determine if a learner has a low score.

    - Skips learners without _id or email.
    - Only considers learners who have not completed the program (progress_status < 100).
    """
    if not learner.get("_id") or not learner.get("email"):
        logger.warning(f"Skipping learner without _id or email: {learner.get('_id')}")
        return False

    progress_status = learner.get("program_data", {}).get("progress_status", 0)
    if progress_status >= 100:
        return False

    return progress_status < settings.low_score_threshold


async def stream_filtered_batches() -> AsyncGenerator[tuple[list[dict], str], None]:
    """
    Async generator that yields learners filtered and batched according to rules:
    - Filtering handled by filter_inactive / filter_low_score
    - Inactive learners and low-score learners separated
    - Batch size taken from .env via settings.batch_size
    - No double classification: inactive takes precedence
    """
    inactive_batch: list[dict] = []
    low_score_batch: list[dict] = []

    async for learner in stream_learners(page_size=batch_size):
        # Decide category (filter_inactive has precedence)
        if filter_inactive(learner):
            inactive_batch.append(learner)
        elif filter_low_score(learner):
            low_score_batch.append(learner)

        # Yield batches when full
        if len(inactive_batch) >= batch_size:
            yield inactive_batch, "inactive"
            inactive_batch.clear()
        if len(low_score_batch) >= batch_size:
            yield low_score_batch, "low_score"
            low_score_batch.clear()

    # Yield remaining learners
    if inactive_batch:
        yield inactive_batch, "inactive"
    if low_score_batch:
        yield low_score_batch, "low_score"
