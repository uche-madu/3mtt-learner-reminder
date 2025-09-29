# main.py
import asyncio
import uuid

from log import setup_logging, logger, set_request_id, clear_request_id
from email_sender.ses_client import send_bulk_emails_with_templates
from data_processing.filters import stream_filtered_batches
from config import settings

setup_logging()


# Optional dry-run mode
async def dry_send_bulk_emails(learners, template_type):
    logger.info(f"[DRY RUN] Would send {len(learners)} {template_type} emails")


async def main(dry_run: bool = False):
    # Assign a request ID for structured logging
    set_request_id(str(uuid.uuid4()))
    logger.info("Starting 3MTT learner email reminder workflow")

    async for learners_batch, template_type in stream_filtered_batches():
        try:
            if dry_run:
                await dry_send_bulk_emails(learners_batch, template_type)
            else:
                await send_bulk_emails_with_templates(
                    learners_batch,
                    template_type=template_type,
                    concurrency=settings.concurrency,
                )
        except Exception as e:
            logger.error(f"Failed to send batch emails ({template_type}): {e}")

    logger.info("Workflow completed")
    clear_request_id()


if __name__ == "__main__":
    # Pass dry_run=True for testing without sending emails
    asyncio.run(main(dry_run=settings.dry_run))
