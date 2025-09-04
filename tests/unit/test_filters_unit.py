# tests/unit/test_filters_unit.py
import pytest
from unittest.mock import patch
from datetime import datetime, timedelta, timezone

from data_processing.filters import (
    filter_inactive,
    filter_low_score,
    stream_filtered_batches,
)


pytestmark = pytest.mark.unit

# Reference date for tests
now = datetime.now(timezone.utc)


# ------------------------
# filter_inactive tests
# ------------------------
@pytest.mark.parametrize(
    "learner,expected",
    [
        # === Core cases ===
        (
            {"_id": "1", "email": "a@test.com", "last_loggedin_date": None},
            True,
        ),  # Null last login
        (
            {
                "_id": "2",
                "email": "b@test.com",
                "last_loggedin_date": (now - timedelta(days=20)).isoformat(),
            },
            True,
        ),  # Old login
        (
            {
                "_id": "3",
                "email": "c@test.com",
                "last_loggedin_date": (now - timedelta(days=1)).isoformat(),
            },
            False,
        ),  # Recent login
        # === Edge cases ===
        ({"_id": "4", "email": None}, False),  # Missing email
        ({"_id": None, "email": "d@test.com"}, False),  # Missing _id
        (
            {"_id": "5", "email": "e@test.com", "last_loggedin_date": "invalid-date"},
            False,
        ),  # Invalid date
        (
            {
                "_id": "6",
                "email": "f@test.com",
                "last_loggedin_date": (now - timedelta(days=20)).isoformat(),
                "program_data": {"progress_status": 100},
            },
            False,
        ),  # Completed learners should not be inactive even if login is >14 days old
        (
            {"_id": "7", "email": "g@test.com"},
            True,
        ),  # Missing last_loggedin_date treated as inactive
    ],
)
def test_filter_inactive(learner, expected):
    assert filter_inactive(learner) == expected


# -------------------------------
# Tests for filter_low_score
# -------------------------------
@pytest.mark.parametrize(
    "learner,threshold,expected",
    [
        # --- Below threshold ---
        (
            {
                "_id": "1",
                "email": "a@test.com",
                "program_data": {"progress_status": 20},
            },
            30,
            True,
        ),
        # --- Above threshold ---
        (
            {
                "_id": "2",
                "email": "b@test.com",
                "program_data": {"progress_status": 50},
            },
            30,
            False,
        ),
        # --- Completed always excluded ---
        (
            {
                "_id": "3",
                "email": "c@test.com",
                "program_data": {"progress_status": 100},
            },
            30,
            False,
        ),
        # --- Edge cases ---
        (
            {"_id": "4", "email": "d@test.com", "program_data": {"progress_status": 0}},
            30,
            True,
        ),  # Zero progress
        (
            {"_id": "5", "email": None, "program_data": {"progress_status": 10}},
            30,
            False,
        ),  # Missing email
        (
            {
                "_id": None,
                "email": "f@test.com",
                "program_data": {"progress_status": 10},
            },
            30,
            False,
        ),  # Missing _id
        # --- Boundary case at threshold ---
        (
            {
                "_id": "6",
                "email": "g@test.com",
                "program_data": {"progress_status": 30},
            },
            30,
            False,
        ),  # Equal to threshold => not low score
        # --- Completed + low score mix ---
        (
            {
                "_id": "7",
                "email": "h@test.com",
                "program_data": {"progress_status": 100},
            },
            200,
            False,
        ),  # Even absurd threshold doesn’t override completion
    ],
)
def test_filter_low_score(learner, threshold, expected, settings):
    # Temporarily override settings.low_score_threshold
    settings.low_score_threshold = threshold
    assert filter_low_score(learner) == expected


@pytest.mark.asyncio
async def test_stream_filtered_batches_classification(learners):
    """Learners are classified via filter_inactive and filter_low_score."""

    async def fake_stream_learners(page_size: int):
        for learner in learners:
            yield learner

    # Mark 1 & 4 as inactive, 2 as low_score
    inactive_side_effects = [True, False, False, True, False, False]

    # Compute only for learners that will actually reach low_score check
    # (i.e. when inactive_side_effects[i] is False)
    low_score_side_effects = []
    for idx, learner in enumerate(learners):
        if not inactive_side_effects[idx]:
            if learner["_id"] == "2":
                low_score_side_effects.append(True)  # learner 2 → low_score
            else:
                low_score_side_effects.append(False)  # everyone else → not low_score

    with (
        patch("data_processing.filters.stream_learners", new=fake_stream_learners),
        patch(
            "data_processing.filters.filter_inactive", side_effect=inactive_side_effects
        ),
        patch(
            "data_processing.filters.filter_low_score",
            side_effect=low_score_side_effects,
        ),
    ):
        results = []
        async for batch, category in stream_filtered_batches():
            results.append((batch, category))

        assert len(results) == 2

        inactive_batch, inactive_cat = results[0]
        low_score_batch, low_score_cat = results[1]

        assert inactive_cat == "inactive"
        assert [learner["_id"] for learner in inactive_batch] == ["1", "4"]

        assert low_score_cat == "low_score"
        assert [learner["_id"] for learner in low_score_batch] == ["2"]


@pytest.mark.asyncio
async def test_stream_filtered_batches_flush_remainders(learners):
    """Remainders are yielded at the end even if not full batch."""

    async def fake_stream_learners(page_size: int):
        for learner in learners:
            yield learner

    with (
        patch("data_processing.filters.stream_learners", new=fake_stream_learners),
        patch("data_processing.filters.filter_inactive", return_value=True),
        patch("data_processing.filters.filter_low_score", return_value=False),
    ):
        results = []
        async for batch, category in stream_filtered_batches():
            results.append((batch, category))

        # All learners should end up in the "inactive" remainder batch
        assert len(results) == 1
        batch, category = results[0]
        assert category == "inactive"
        assert [learner["_id"] for learner in batch] == [
            learner["_id"] for learner in learners
        ]
