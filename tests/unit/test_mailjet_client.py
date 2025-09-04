# tests/unit/test_mailjet_client.py
import pytest
from email_sender import mailjet_client as mj
from email_sender.templates import INACTIVE_TEMPLATE, LOW_SCORE_TEMPLATE
from httpx import AsyncClient

pytestmark = pytest.mark.unit


# -----------------------------
# Helper FakeClient & Response
# -----------------------------
class FakeResponse:
    def __init__(self, status_code=200, text=""):
        self.status_code = status_code
        self.text = text

    def json(self):
        return {"success": True}


class FakeClient(AsyncClient):
    def __init__(self, status_code=200, text=""):
        self._status_code = status_code
        self._text = text

    async def post(self, url, json):
        return FakeResponse(self._status_code, self._text)


# -----------------------------
# Chunking tests
# -----------------------------
@pytest.mark.asyncio
async def test_chunked_yields_correctly():
    data = [{"_id": str(i)} for i in range(105)]
    chunks = list(mj.chunked(data, 50))
    assert len(chunks) == 3
    assert len(chunks[0]) == 50
    assert len(chunks[1]) == 50
    assert len(chunks[2]) == 5


# -----------------------------
# _send_email tests
# -----------------------------
@pytest.mark.asyncio
async def test_send_email_success_logs_info(mocker):
    sent_logs = []
    client = FakeClient(status_code=200)
    mocker.patch.object(
        mj.logger, "info", side_effect=lambda msg: sent_logs.append(msg)
    )
    mocker.patch.object(
        mj.logger, "error", side_effect=lambda msg: sent_logs.append(msg)
    )

    payload = {"Messages": [{"To": [{"Email": "a@test.com"}]}]}
    await mj._send_email(client, payload, "test_batch")

    assert any("sent successfully" in msg for msg in sent_logs)


@pytest.mark.asyncio
async def test_send_email_failure_logs_error(mocker):
    sent_logs = []
    client = FakeClient(status_code=500, text="Server error")
    mocker.patch.object(
        mj.logger, "info", side_effect=lambda msg: sent_logs.append(msg)
    )
    mocker.patch.object(
        mj.logger, "error", side_effect=lambda msg: sent_logs.append(msg)
    )

    payload = {"Messages": [{"To": [{"Email": "a@test.com"}]}]}
    await mj._send_email(client, payload, "fail_batch")

    assert any("failed" in msg for msg in sent_logs)


# -----------------------------
# send_batch_emails tests
# -----------------------------
@pytest.mark.asyncio
async def test_send_batch_emails_sends_in_batches_for_both_templates(mocker):
    # Prepare 120 learners
    learners = [
        {"_id": str(i), "email": f"user{i}@test.com", "firstName": "Test"}
        for i in range(120)
    ]
    sent_batches = []

    async def fake_send_email(client, payload, batch_id):
        sent_batches.append((batch_id, len(payload["Messages"])))

    mocker.patch("email_sender.mailjet_client._send_email", new=fake_send_email)

    # Disable test mode
    mocker.patch.object(mj.settings, "test_mode", False)
    mocker.patch.object(mj.settings, "test_email_address", None)

    # Send using inactive template
    await mj.send_batch_emails(learners, template_type="inactive")
    # Send using low_score template
    await mj.send_batch_emails(learners, template_type="low_score")

    # Check inactive batches
    inactive_batches = [b for b in sent_batches if b[0].startswith("inactive_batch_")]
    assert inactive_batches[0][1] == 50
    assert inactive_batches[1][1] == 50
    assert inactive_batches[2][1] == 20
    assert all(b[0].startswith("inactive_batch_") for b in inactive_batches)

    # Check low_score batches
    low_score_batches = [b for b in sent_batches if b[0].startswith("low_score_batch_")]
    assert low_score_batches[0][1] == 50
    assert low_score_batches[1][1] == 50
    assert low_score_batches[2][1] == 20
    assert all(b[0].startswith("low_score_batch_") for b in low_score_batches)


@pytest.mark.asyncio
async def test_send_batch_emails_skips_missing_email(mocker):
    learners = [
        {"_id": "1", "firstName": "Alice", "email": "a@test.com"},
        {"_id": "2", "firstName": "Bob"},  # missing email
    ]
    sent_batches = []

    async def fake_send_email(client, payload, batch_id):
        sent_batches.append(payload)

    mocker.patch("email_sender.mailjet_client._send_email", new=fake_send_email)

    # Disable test mode so missing emails are skipped
    mocker.patch.object(mj.settings, "test_mode", False)
    mocker.patch.object(mj.settings, "test_email_address", None)

    await mj.send_batch_emails(learners, template_type="inactive")

    # Only 1 learner sent
    assert len(sent_batches[0]["Messages"]) == 1
    assert sent_batches[0]["Messages"][0]["To"][0]["Email"] == "a@test.com"


@pytest.mark.asyncio
async def test_send_batch_emails_test_mode_overrides_email(mocker):
    learners = [{"_id": "1", "email": "a@test.com", "firstName": "Alice"}]

    mocker.patch.object(mj.settings, "test_mode", True)
    mocker.patch.object(mj.settings, "test_email_address", "test@override.com")

    sent_batches = []

    async def fake_send_email(client, payload, batch_id):
        sent_batches.append(payload)

    mocker.patch("email_sender.mailjet_client._send_email", new=fake_send_email)
    await mj.send_batch_emails(learners, template_type="inactive")

    assert sent_batches[0]["Messages"][0]["To"][0]["Email"] == "test@override.com"


@pytest.mark.asyncio
async def test_send_batch_emails_uses_low_score_template(mocker):
    learners = [{"_id": "1", "email": "a@test.com", "firstName": "Alice"}]

    mocker.patch.object(mj.settings, "test_mode", False)
    mocker.patch.object(mj.settings, "test_email_address", None)

    sent_batches = []

    async def fake_send_email(client, payload, batch_id):
        sent_batches.append(payload)

    mocker.patch("email_sender.mailjet_client._send_email", new=fake_send_email)
    await mj.send_batch_emails(learners, template_type="low_score")

    assert sent_batches[0]["Messages"][0]["Subject"] == LOW_SCORE_TEMPLATE["subject"]
    assert "Alice" in sent_batches[0]["Messages"][0]["TextPart"]


@pytest.mark.asyncio
async def test_send_batch_emails_uses_inactive_template(mocker):
    learners = [{"_id": "1", "email": "a@test.com", "firstName": "Alice"}]

    mocker.patch.object(mj.settings, "test_mode", False)
    mocker.patch.object(mj.settings, "test_email_address", None)

    sent_batches = []

    async def fake_send_email(client, payload, batch_id):
        sent_batches.append(payload)

    mocker.patch("email_sender.mailjet_client._send_email", new=fake_send_email)

    await mj.send_batch_emails(learners, template_type="inactive")

    batch = sent_batches[0]["Messages"][0]
    assert batch["Subject"] == INACTIVE_TEMPLATE["subject"]
    assert "Alice" in batch["TextPart"]
    assert (
        batch["HTMLPart"].startswith("<") or "Alice" in batch["HTMLPart"]
    )  # if HTML exists


@pytest.mark.asyncio
async def test_send_batch_emails_correct_groups(mocker):
    learners = [
        {
            "_id": "1",
            "email": "inactive@test.com",
            "firstName": "InactiveUser",
            "score": 10,
            "active": False,
        },
        {
            "_id": "2",
            "email": "low@test.com",
            "firstName": "LowScoreUser",
            "score": 40,
            "active": True,
        },
    ]

    sent_batches = []

    async def fake_send_email(client, payload, batch_id):
        sent_batches.append((batch_id, payload["Messages"]))

    mocker.patch("email_sender.mailjet_client._send_email", new=fake_send_email)
    mocker.patch.object(mj.settings, "test_mode", False)
    mocker.patch.object(mj.settings, "test_email_address", None)

    inactive_learners = [
        learner for learner in learners if not learner.get("active", True)
    ]
    low_score_learners = [
        learner
        for learner in learners
        if learner.get("score", 0) < 50 and learner.get("active", True)
    ]

    await mj.send_batch_emails(inactive_learners, template_type="inactive")
    await mj.send_batch_emails(low_score_learners, template_type="low_score")

    for batch_id, msgs in sent_batches:
        emails = [m["To"][0]["Email"] for m in msgs]
        if batch_id.startswith("inactive_batch_"):
            assert "inactive@test.com" in emails
            assert "low@test.com" not in emails
        if batch_id.startswith("low_score_batch_"):
            assert "low@test.com" in emails
            assert "inactive@test.com" not in emails
