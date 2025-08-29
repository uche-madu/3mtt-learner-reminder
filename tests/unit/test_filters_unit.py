# tests/unit/test_filters_unit.py
import pytest
from datetime import datetime, timedelta, timezone

from data_processing.filters import filter_inactive, filter_low_score

pytestmark = pytest.mark.unit

# Reference date for tests
now = datetime.now(timezone.utc)


@pytest.mark.parametrize(
    "learner,expected",
    [
        (
            {"_id": "1", "email": "a@test.com", "last_loggedin_date": None},
            True,
        ),  # Null last login => inactive
        (
            {
                "_id": "2",
                "email": "b@test.com",
                "last_loggedin_date": (now - timedelta(days=20)).isoformat(),
            },
            True,
        ),  # old login => inactive
        (
            {
                "_id": "3",
                "email": "c@test.com",
                "last_loggedin_date": (now - timedelta(days=1)).isoformat(),
            },
            False,
        ),  # recent login => active
        ({"_id": "4", "email": None}, False),  # missing email => skip
        ({"_id": None, "email": "d@test.com"}, False),  # missing _id => skip
        (
            {"_id": "5", "email": "e@test.com", "last_loggedin_date": "invalid-date"},
            False,
        ),  # invalid date format
    ],
)
def test_filter_inactive(learner, expected):
    assert filter_inactive(learner) == expected


@pytest.mark.parametrize(
    "learner,threshold,expected",
    [
        (
            {
                "_id": "1",
                "email": "a@test.com",
                "program_data": {"progress_status": 20},
            },
            30,
            True,
        ),  # below threshold
        (
            {
                "_id": "2",
                "email": "b@test.com",
                "program_data": {"progress_status": 50},
            },
            30,
            False,
        ),  # above threshold
        (
            {
                "_id": "3",
                "email": "c@test.com",
                "program_data": {"progress_status": 100},
            },
            30,
            False,
        ),  # completed
        (
            {"_id": "4", "email": "d@test.com", "program_data": {"progress_status": 0}},
            30,
            True,
        ),  # zero progress
        (
            {"_id": "5", "email": None, "program_data": {"progress_status": 10}},
            30,
            False,
        ),  # missing email
        (
            {
                "_id": None,
                "email": "f@test.com",
                "program_data": {"progress_status": 10},
            },
            30,
            False,
        ),  # missing _id
    ],
)
def test_filter_low_score(learner, threshold, expected, settings):
    # Temporarily override settings.low_score_threshold
    settings.low_score_threshold = threshold
    assert filter_low_score(learner) == expected
