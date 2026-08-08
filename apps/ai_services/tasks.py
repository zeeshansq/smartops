import logging
from celery import shared_task
from django.db import transaction

from .models import AIRequestLog
from .services import LLMService, LLMServiceError

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def process_ai_request(self, log_id: str):
    """
    Celery background task to execute asynchronous LLM generation.

    Task Execution Lifecycle:
    1. Fetch AIRequestLog by ID.
    2. Set status to 'PROCESSING'.
    3. Invoke LLMService.generate(prompt).
    4. On Success: Set status to 'COMPLETED', store response payload & tokens_used.
    5. On Failure: Record sanitized error message & set status to 'FAILED'.
       Retry up to 3 times on transient errors.
    """
    try:
        log = AIRequestLog.objects.get(pk=log_id)
    except AIRequestLog.DoesNotExist:
        logger.error("process_ai_request: AIRequestLog with id %s not found.", log_id)
        return

    # Update status to PROCESSING atomically
    with transaction.atomic():
        log.status = AIRequestLog.STATUS_PROCESSING
        log.save(update_fields=['status', 'updated_at'])

    logger.info(
        "Processing AI request task %s (log_id=%s, org=%s)",
        self.request.id,
        log.id,
        log.organization.name,
    )

    try:
        service = LLMService()
        result = service.generate(log.prompt)

        with transaction.atomic():
            log.status = AIRequestLog.STATUS_COMPLETED
            log.response = result
            log.tokens_used = result.get('tokens_used', 0)
            log.save(update_fields=['status', 'response', 'tokens_used', 'updated_at'])

        logger.info(
            "AI request completed successfully: log_id=%s, tokens_used=%d",
            log.id,
            log.tokens_used,
        )

    except LLMServiceError as exc:
        logger.warning(
            "LLMService error for log_id=%s: %s (attempt %d/%d)",
            log.id,
            str(exc),
            self.request.retries + 1,
            self.max_retries + 1,
        )
        # Update log status to FAILED
        with transaction.atomic():
            log.status = AIRequestLog.STATUS_FAILED
            log.error_message = f"AI Generation Failed: {str(exc)}"
            log.save(update_fields=['status', 'error_message', 'updated_at'])

        if self.request.retries < self.max_retries:
            try:
                self.retry(exc=exc)
            except Exception:
                pass

    except Exception as exc:
        logger.exception("Unexpected error processing AI request log_id=%s", log.id)
        with transaction.atomic():
            log.status = AIRequestLog.STATUS_FAILED
            log.error_message = "Internal processing error occurred."
            log.save(update_fields=['status', 'error_message', 'updated_at'])
