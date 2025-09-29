# email_sender/ses_client.py
import asyncio
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from botocore.client import BaseClient
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

from config import settings
from log import logger
from utils.retry import is_transient_error, log_before_retry
from email_sender.templates import INACTIVE_TEMPLATE, LOW_SCORE_TEMPLATE

DB_PATH = Path(settings.data_dir) / "emails_sent.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


# ---------------------------
# SQLite tracking functions
# ---------------------------
def init_db() -> None:
    """Create emails_sent table if it doesn't exist."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS emails_sent (
                email TEXT NOT NULL,
                template_type TEXT NOT NULL,
                sent_at TIMESTAMP NOT NULL,
                status TEXT NOT NULL,
                PRIMARY KEY(email, template_type)
            )
            """
        )
        conn.commit()


def has_been_sent(email: str, template_type: str) -> bool:
    """Check if an email has already been sent this week."""
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            "SELECT 1 FROM emails_sent WHERE email=? AND template_type=? AND sent_at>=?",
            (email, template_type, week_ago.isoformat()),
        )
        return cur.fetchone() is not None


def record_sent(email: str, template_type: str, status: str) -> None:
    """Record email sent attempt in SQLite."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO emails_sent (email, template_type, sent_at, status) VALUES (?, ?, ?, ?)",
            (email, template_type, datetime.now(timezone.utc).isoformat(), status),
        )
        conn.commit()


# ---------------------------
# SES functions
# ---------------------------
def _get_ses_client() -> BaseClient:
    return boto3.client(
        "ses",
        region_name=settings.email_region,
        aws_access_key_id=settings.email_host_user.get_secret_value(),
        aws_secret_access_key=settings.email_host_password.get_secret_value(),
    )


@retry(
    stop=stop_after_attempt(settings.max_retries),
    wait=wait_exponential(multiplier=settings.retry_delay, min=1, max=60),
    retry=retry_if_exception(is_transient_error),
    before_sleep=log_before_retry,
    reraise=True,
)
def _send_email_ses(
    to_email: str, subject: str, html_content: str, text_content: str
) -> None:
    """Blocking SES send with retries."""
    try:
        client = _get_ses_client()
        logger.debug(f"Sending SES email to {to_email} with subject '{subject}'")
        client.send_email(
            Source=f"{settings.origin_name} <{settings.origin_email.get_secret_value()}>",
            Destination={"ToAddresses": [to_email]},
            Message={
                "Subject": {"Data": subject},
                "Body": {
                    "Html": {"Data": html_content},
                    "Text": {"Data": text_content},
                },
            },
        )
        logger.info(f"Email sent to {to_email}")
    except (BotoCoreError, ClientError) as e:
        logger.error(f"Failed to send SES email to {to_email}: {e}")
        raise


@retry(
    stop=stop_after_attempt(settings.max_retries),
    wait=wait_exponential(multiplier=settings.retry_delay, min=1, max=60),
    retry=retry_if_exception(is_transient_error),
    before_sleep=log_before_retry,
    reraise=True,
)
def _send_email_smtp(
    to_email: str, subject: str, html_content: str, text_content: str
) -> None:
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = (
            f"{settings.origin_name} <{settings.origin_email.get_secret_value()}>"
        )
        msg["To"] = to_email

        msg.attach(MIMEText(text_content, "plain"))
        msg.attach(MIMEText(html_content, "html"))

        with smtplib.SMTP(settings.email_host, settings.email_port) as server:
            if settings.email_use_tls:
                server.starttls()
            server.login(
                settings.email_host_user.get_secret_value(),
                settings.email_host_password.get_secret_value(),
            )
            server.sendmail(
                settings.origin_email.get_secret_value(), to_email, msg.as_string()
            )
        logger.info(f"Email sent to {to_email}")
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        raise


async def send_email(
    to_email: str, subject: str, html_content: str, text_content: str
) -> None:
    """Async wrapper to send email via SES or SMTP, respecting test mode."""
    original_email = to_email
    if settings.test_mode:
        to_email = settings.test_email_address
        logger.info(
            f"TEST_MODE active: redirecting email from {original_email} to {to_email}"
        )

    if settings.use_smtp:
        await asyncio.to_thread(
            _send_email_smtp, to_email, subject, html_content, text_content
        )
    else:
        await asyncio.to_thread(
            _send_email_ses, to_email, subject, html_content, text_content
        )


# ---------------------------
# Bulk email function
# ---------------------------
async def send_bulk_emails_with_templates(
    learners: List[dict], template_type: str = "inactive", concurrency: int = 5
) -> None:
    """
    Send templated emails to learners concurrently via SES API.
    Tracks sent emails in SQLite to avoid duplicates within a week.
    """
    init_db()

    template_map = {"inactive": INACTIVE_TEMPLATE, "low_score": LOW_SCORE_TEMPLATE}
    template = template_map.get(template_type)
    if not template:
        logger.error(f"Unknown template_type: {template_type}")
        return

    semaphore = asyncio.Semaphore(concurrency)
    sent_count = 0
    logger.info(
        f"Sending {len(learners)} emails using template '{template_type}' with concurrency={concurrency}"
    )

    async def send_one(learner: dict):
        nonlocal sent_count
        async with semaphore:
            to_email = learner.get("email")
            if not to_email:
                logger.warning(
                    f"Learner {learner.get('_id', 'no_id')} has no email, skipping"
                )
                return

            # Skip if already sent this week
            if not settings.test_mode and has_been_sent(to_email, template_type):
                logger.info(
                    f"Skipping {to_email}, already sent {template_type} this week"
                )
                return

            # Apply test_mode limit
            if (
                settings.test_mode
                and settings.test_mode_count
                and sent_count >= settings.test_mode_count
            ):
                return

            name = learner.get("firstName", "").title().strip()
            if not name:
                logger.warning(
                    f"Learner {learner.get('_id', 'no_id')} has no firstName"
                )
            subject = template["subject"]
            text_content = template["body"].format(first_name=name)
            html_content = template.get("html", template["body"]).format(
                first_name=name
            )

            try:
                await send_email(to_email, subject, html_content, text_content)
                record_sent(to_email, template_type, status="success")
            except Exception:
                record_sent(to_email, template_type, status="failed")

            sent_count += 1

    await asyncio.gather(*(send_one(learner) for learner in learners))
    logger.info("Finished sending all learner emails")

    # --- Summary logging ---
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            "SELECT status, COUNT(*) FROM emails_sent WHERE sent_at >= ? AND template_type = ? GROUP BY status",
            (datetime.now(timezone.utc) - timedelta(minutes=5), template_type),
        )
        stats = dict(cur.fetchall())

    total_sent = stats.get("success", 0)
    total_failed = stats.get("failed", 0)
    total = total_sent + total_failed
    success_rate = (total_sent / total * 100) if total > 0 else 0.0

    logger.info(
        f"Summary for template '{template_type}': "
        f"sent={total_sent}, failed={total_failed}, total={total}, success_rate={success_rate:.2f}%"
    )
