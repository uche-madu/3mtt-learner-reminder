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
    - TEST_MODE limits the number of learners yielded per template
    """
    inactive_batch: list[dict] = []
    low_score_batch: list[dict] = []

    # Counters
    inactive_sent = 0
    low_score_sent = 0
    inactive_total = 0
    low_score_total = 0
    skipped_total = 0
    inactive_yielded = 0
    low_score_yielded = 0

    if settings.test_mode:
        test_limit = settings.test_mode_count

    logger.info(f"Starting stream_filtered_batches (TEST_MODE={settings.test_mode})")

    async for learner in stream_learners(batch_size=batch_size):
        try:
            is_inactive = filter_inactive(learner)
            is_low_score = filter_low_score(learner) if not is_inactive else False

            # Increment total counters
            if is_inactive:
                inactive_total += 1
            elif is_low_score:
                low_score_total += 1
            else:
                skipped_total += 1

            # Add to batch (respect test mode)
            if is_inactive and (not settings.test_mode or inactive_sent < test_limit):
                inactive_batch.append(learner)
                inactive_sent += 1
                logger.debug(
                    f"Added learner {learner.get('_id')} to inactive batch "
                    f"({inactive_sent}/{test_limit if settings.test_mode else '∞'})"
                )
            elif is_low_score and (
                not settings.test_mode or low_score_sent < test_limit
            ):
                low_score_batch.append(learner)
                low_score_sent += 1
                logger.debug(
                    f"Added learner {learner.get('_id')} to low_score batch "
                    f"({low_score_sent}/{test_limit if settings.test_mode else '∞'})"
                )

            # Yield batches when full
            if len(inactive_batch) >= batch_size:
                logger.info(
                    f"Yielding inactive batch of {len(inactive_batch)} learners"
                )
                inactive_yielded += len(inactive_batch)
                yield inactive_batch, "inactive"
                inactive_batch.clear()

            if len(low_score_batch) >= batch_size:
                logger.info(
                    f"Yielding low_score batch of {len(low_score_batch)} learners"
                )
                low_score_yielded += len(low_score_batch)
                yield low_score_batch, "low_score"
                low_score_batch.clear()

            # Stop early if test mode limits reached
            if (
                settings.test_mode
                and inactive_sent >= test_limit
                and low_score_sent >= test_limit
            ):
                logger.info(
                    "TEST_MODE limits reached; yielding remaining batches and stopping"
                )

                if inactive_batch:
                    inactive_yielded += len(inactive_batch)
                    yield (
                        inactive_batch[
                            : max(0, test_limit - (inactive_sent - len(inactive_batch)))
                        ],
                        "inactive",
                    )
                if low_score_batch:
                    low_score_yielded += len(low_score_batch)
                    yield (
                        low_score_batch[
                            : max(
                                0, test_limit - (low_score_sent - len(low_score_batch))
                            )
                        ],
                        "low_score",
                    )

                return

        except Exception as e:
            logger.error(
                f"Error processing learner {learner.get('_id')}: {e}", exc_info=True
            )

    # Yield any remaining learners
    try:
        if inactive_batch:
            inactive_yielded += len(inactive_batch)
            yield (
                inactive_batch
                if not settings.test_mode
                else inactive_batch[: max(0, test_limit - inactive_sent)],
                "inactive",
            )
        if low_score_batch:
            low_score_yielded += len(low_score_batch)
            yield (
                low_score_batch
                if not settings.test_mode
                else low_score_batch[: max(0, test_limit - low_score_sent)],
                "low_score",
            )

        # Final summary log
        total_learners = inactive_total + low_score_total + skipped_total
        logger.info(
            f"Filter summary: total={total_learners}, "
            f"inactive_total={inactive_total}, inactive_yielded={inactive_yielded}, "
            f"low_score_total={low_score_total}, low_score_yielded={low_score_yielded}, "
            f"skipped_total={skipped_total}, "
            f"percent_inactive_sent={inactive_yielded / inactive_total * 100 if inactive_total else 0:.1f}%, "
            f"percent_low_score_sent={low_score_yielded / low_score_total * 100 if low_score_total else 0:.1f}%"
        )

    except Exception as e:
        logger.error(f"Error yielding final batches: {e}", exc_info=True)
