# # tests/integration/test_filters_async.py
# import pytest
# from datetime import datetime, timedelta, timezone
# import pytest_asyncio

# from data_processing.filters import stream_filtered_batches

# now = datetime.now(timezone.utc)

# pytestmark = pytest.mark.integration


# @pytest.mark.asyncio
# async def test_stream_filtered_batches(monkeypatch, settings):
#     """Test async batch generator with mock learners."""
#     # Create test learners
#     learners = [
#         {
#             "_id": "1",
#             "email": "inactive1@test.com",
#             "program_data": {"progress_status": 10},
#             "last_loggedin_date": None,
#         },  # inactive
#         {
#             "_id": "2",
#             "email": "inactive2@test.com",
#             "program_data": {"progress_status": 20},
#             "last_loggedin_date": "2025-07-01T00:00:00+00:00",
#         },  # inactive
#         {
#             "_id": "3",
#             "email": "low1@test.com",
#             "program_data": {"progress_status": 25},
#             "last_loggedin_date": "2025-08-20T00:00:00+00:00",
#         },  # low-score
#         {
#             "_id": "4",
#             "email": "completed@test.com",
#             "program_data": {"progress_status": 100},
#             "last_loggedin_date": "2025-08-20T00:00:00+00:00",
#         },  # completed
#     ]

#     async def mock_stream_learners(page_size=None):
#         for learner in learners:
#             yield learner

#     monkeypatch.setattr(
#         "data_processing.downloader.stream_learners", mock_stream_learners
#     )

#     settings.batch_size = 2
#     settings.low_score_threshold = 30

#     batches = []
#     async for batch, category in stream_filtered_batches():
#         batches.append((category, [learner["_id"] for learner in batch]))

#     # Extract IDs by category
#     inactive_ids = [i for cat, ids in batches if cat == "inactive" for i in ids]
#     low_score_ids = [i for cat, ids in batches if cat == "low_score" for i in ids]

#     assert "1" in inactive_ids
#     assert "2" in inactive_ids
#     assert "3" in low_score_ids
#     assert "4" not in inactive_ids
#     assert "4" not in low_score_ids


# @pytest_asyncio.fixture
# async def learners() -> list[dict]:
#     """
#     Fixture providing learners with varied data for classification tests.
#     Covers inactive, low-score, completed, and invalid cases.
#     """
#     return [
#         # Inactive learner (>40 days)
#         {
#             "_id": "1",
#             "email": "inactive@test.com",
#             "last_loggedin_date": (now - timedelta(days=40)).isoformat(),
#             "program_data": {"progress_status": 80},
#         },
#         # Low-score learner (recent login, low progress)
#         {
#             "_id": "2",
#             "email": "low@test.com",
#             "last_loggedin_date": (now - timedelta(days=1)).isoformat(),
#             "program_data": {"progress_status": 10},
#         },
#         # Completed learner (should be skipped)
#         {
#             "_id": "3",
#             "email": "completed@test.com",
#             "last_loggedin_date": (now - timedelta(days=1)).isoformat(),
#             "program_data": {"progress_status": 100},
#         },
#         # Inactive + low score → should be classified as inactive only
#         {
#             "_id": "4",
#             "email": "conflict@test.com",
#             "last_loggedin_date": (now - timedelta(days=40)).isoformat(),
#             "program_data": {"progress_status": 10},
#         },
#         # Missing email → should be skipped
#         {
#             "_id": "5",
#             "email": None,
#             "last_loggedin_date": (now - timedelta(days=1)).isoformat(),
#             "program_data": {"progress_status": 10},
#         },
#         # Missing _id → should be skipped
#         {
#             "_id": None,
#             "email": "noid@test.com",
#             "last_loggedin_date": (now - timedelta(days=1)).isoformat(),
#             "program_data": {"progress_status": 20},
#         },
#     ]
