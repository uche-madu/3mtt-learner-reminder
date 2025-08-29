# tests/test_main.py
import asyncio
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from log import setup_logging, logger, set_request_id, clear_request_id
from data_processing.filters import stream_filtered_batches
from config import settings


# Mock the email sending
async def mock_send_batch_emails(learners, template_type):
    logger.info(
        f"[MOCK] Sending {len(learners)} '{template_type}' emails: "
        + ", ".join([learner.get("_id", "no_id") for learner in learners])
    )
    await asyncio.sleep(0.05)  # simulate network latency


# Mock the stream of learners (replace API calls)
async def mock_learner_generator():
    two_weeks_ago = datetime.now(timezone.utc) - timedelta(days=settings.inactive_days)
    sample_learners = [
        {
            "_id": "1",
            "email": "a@example.com",
            "firstName": "Alice",
            "program_data": {"progress_status": 30},
            "last_loggedin_date": (two_weeks_ago - timedelta(days=1)).isoformat(),
        },
        {
            "_id": "2",
            "email": "b@example.com",
            "firstName": "Bob",
            "program_data": {"progress_status": 100},
            "last_loggedin_date": (two_weeks_ago - timedelta(days=10)).isoformat(),
        },
        {
            "_id": "3",
            "email": "c@example.com",
            "firstName": "Charlie",
            "program_data": {"progress_status": 40},
            "last_loggedin_date": (two_weeks_ago + timedelta(days=1)).isoformat(),
        },
        {
            "_id": "4",
            "email": None,
            "firstName": "NoEmail",
            "program_data": {"progress_status": 20},
            "last_loggedin_date": None,
        },
        {
            "_id": None,
            "email": "noid@example.com",
            "firstName": "NoID",
            "program_data": {"progress_status": 20},
            "last_loggedin_date": None,
        },
    ]
    for learner in sample_learners:
        yield learner


@pytest.mark.asyncio
async def test_stream_filtered_batches():
    setup_logging()
    set_request_id(str(uuid.uuid4()))
    logger.info("Starting TEST stream_filtered_batches workflow")

    # Use the mock generator
    async for batch in stream_filtered_batches():
        # Each batch is a dict with 'inactive' and 'low_score' keys containing learners
        inactive = batch.get("inactive", [])
        low_score = batch.get("low_score", [])

        # Assert no learner has progress_status == 100
        for learner in inactive + low_score:
            assert learner["program_data"]["progress_status"] != 100

        # Assert no learner without email or _id is in batch
        for learner in inactive + low_score:
            assert learner.get("_id") is not None
            assert learner.get("email") is not None

    logger.info("TEST stream_filtered_batches workflow completed")
    clear_request_id()
