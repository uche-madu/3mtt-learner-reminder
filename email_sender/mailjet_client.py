# email_sender/mailjet_client.py
import asyncio
import httpx
import traceback
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

from config import settings
from log import logger
from email_sender.templates import INACTIVE_TEMPLATE, LOW_SCORE_TEMPLATE
from utils.retry import is_transient_error, log_before_retry


async def send_batch_emails(learners: list[dict], template_type: str = "inactive"):
    """
    Send a batch of emails to learners, using either inactive or low_score templates.
    Respects test mode and overrides recipients if needed.
    """
    template_map = {"inactive": INACTIVE_TEMPLATE, "low_score": LOW_SCORE_TEMPLATE}
    template = template_map.get(template_type)
    if not template:
        logger.error(f"Unknown template_type: {template_type}")
        return

    async with httpx.AsyncClient(
        auth=(
            settings.mailjet_api_key.get_secret_value(),
            settings.mailjet_api_secret.get_secret_value(),
        ),
        timeout=30.0,
    ) as client:
        tasks = []
        for learner in learners:
            # Determine recipient email (override in test mode)
            to_email = (
                settings.test_email_address
                if settings.test_mode and settings.test_email_address
                else learner.get("email")
            )

            if not to_email:
                learner_id = learner.get("_id", "no_id")
                logger.warning(f"Learner {learner_id} has no email, skipping")
                continue

            if settings.test_mode:
                logger.info(f"[TEST MODE] Overriding recipient to {to_email}")

            name = learner.get("firstName", "").title().strip()
            if not name:
                logger.warning(
                    f"Learner {learner.get('_id', 'no_id')} has no firstName"
                )

            payload = {
                "Messages": [
                    {
                        "From": {
                            "Email": settings.origin_email.get_secret_value(),
                            "Name": settings.origin_name.get_secret_value(),
                        },
                        "To": [{"Email": to_email, "Name": name}],
                        "Subject": template["subject"],
                        "TextPart": template["body"].format(first_name=name),
                        "HTMLPart": template.get("html", template["body"]).format(
                            first_name=name
                        ),
                    }
                ]
            }

            tasks.append(asyncio.create_task(_send_email(client, payload, to_email)))

        await asyncio.gather(*tasks)


@retry(
    stop=stop_after_attempt(settings.max_retries),
    wait=wait_exponential(multiplier=settings.retry_delay, min=1, max=60),
    retry=retry_if_exception(is_transient_error),
    before_sleep=log_before_retry,
    reraise=True,
)
async def _send_email(client: httpx.AsyncClient, payload: dict, to_email: str):
    """Send a single email via Mailjet with retries and detailed logging."""
    url = "https://api.mailjet.com/v3.1/send"
    try:
        resp = await client.post(url, json=payload)
        if resp.status_code != 200:
            logger.error(
                f"Failed to send email to {to_email} | Status: {resp.status_code} | Response: {resp.text}"
            )
        else:
            logger.info(f"Email sent successfully to {to_email}")
    except Exception as e:
        tb = traceback.format_exc()
        logger.error(
            f"Exception sending email to {to_email} | Type: {type(e).__name__} | "
            f"Message: {str(e)} | Traceback:\n{tb}"
        )
        raise  # re-raise so tenacity can retry if transient
