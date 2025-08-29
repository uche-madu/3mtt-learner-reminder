# main.py
import asyncio
import uuid

from log import setup_logging, logger, set_request_id, clear_request_id
from email_sender.mailjet_client import send_batch_emails
from data_processing.filters import stream_filtered_batches

setup_logging()


# For DRY RUN purposes, replace send_batch_emails with a mock function
async def dry_send_batch_emails(learners, template_type):
    logger.info(f"[DRY RUN] Would send {len(learners)} {template_type} emails")


async def main():
    # Assign a request ID for structured logging
    set_request_id(str(uuid.uuid4()))
    logger.info("Starting 3MTT learner email reminder workflow")

    async for learners_batch, template_type in stream_filtered_batches():
        try:
            await send_batch_emails(learners_batch, template_type=template_type)
        except Exception as e:
            logger.error(f"Failed to send batch emails ({template_type}): {e}")

    logger.info("Workflow completed")
    clear_request_id()


if __name__ == "__main__":
    asyncio.run(main())
