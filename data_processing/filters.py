# data_processing/filters.py
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator

from config import settings
from log import logger
from data_processing.downloader import stream_learners

two_weeks_ago = datetime.now(timezone.utc) - timedelta(days=settings.inactive_days)


def filter_inactive(learner: dict) -> bool:
    """
    Determine if a learner is inactive.

    - Learners with no last_loggedin_date are treated as inactive.
    - Logs invalid date formats but continues processing.
    """
    if not learner.get("_id") or not learner.get("email"):
        logger.warning(f"Skipping learner without _id or email: {learner.get('_id')}")
        return False

    last_login = learner.get("last_loggedin_date")
    if not last_login:
        return True  # Treat null as inactive

    try:
        last_login_dt = datetime.fromisoformat(last_login.replace("Z", "+00:00"))
    except Exception:
        logger.warning(f"Invalid last_loggedin_date for learner {learner['_id']}")
        return False

    return last_login_dt < two_weeks_ago


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


async def stream_filtered_batches() -> AsyncGenerator:
    """
    Async generator that yields learners filtered and batched according to rules:
    - Skip learners with no email (logs _id)
    - Skip learners with progress_status == 100
    - Inactive learners and low-score learners separated
    - Batch size taken from .env via settings.batch_size
    """
    inactive_batch = []
    low_score_batch = []

    async for learner in stream_learners(page_size=settings.batch_size):
        learner_id = learner.get("_id")
        email = learner.get("email")
        if not learner_id:
            logger.warning("Learner missing _id, skipping")
            continue
        if not email:
            logger.warning(f"Learner {learner_id} has no email, skipping")
            continue

        progress = learner.get("program_data", {}).get("progress_status", 0)
        if progress == 100:
            continue

        # Determine category
        last_login = learner.get("last_loggedin_date")
        if (
            not last_login
            or datetime.fromisoformat(last_login.replace("Z", "+00:00")) < two_weeks_ago
        ):
            inactive_batch.append(learner)
        else:
            if progress < settings.low_score_threshold:
                low_score_batch.append(learner)

        # Yield batches when full
        if len(inactive_batch) >= settings.batch_size:
            yield inactive_batch, "inactive"
            inactive_batch.clear()
        if len(low_score_batch) >= settings.batch_size:
            yield low_score_batch, "low_score"
            low_score_batch.clear()

    # Yield remaining learners
    if inactive_batch:
        yield inactive_batch, "inactive"
    if low_score_batch:
        yield low_score_batch, "low_score"
