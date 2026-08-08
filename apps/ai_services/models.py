import uuid
import logging
from django.db import models
from django.conf import settings

logger = logging.getLogger(__name__)


class AIRequestLog(models.Model):
    """
    Logs asynchronous AI request execution, status, token usage, and structured response.

    Security & Data Isolation Design Decisions:
    - `id`: UUID primary key prevents sequential ID enumeration attacks.
    - `organization`: Scopes all request records to a specific tenant (workspace).
    - `user`: Tracks identity of the user initiating the AI operation for audit.
    - `task_id`: Celery task ID, indexed for fast status lookup.
    - `status`: Choices tracking job lifecycle ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED').
    - `tokens_used`: Usage counter for billing/quota auditing.
    - `error_message`: Sanitized error output recorded on failure (no credentials/keys).
    """

    STATUS_PENDING = 'PENDING'
    STATUS_PROCESSING = 'PROCESSING'
    STATUS_COMPLETED = 'COMPLETED'
    STATUS_FAILED = 'FAILED'

    STATUS_CHOICES = (
        (STATUS_PENDING, 'Pending'),
        (STATUS_PROCESSING, 'Processing'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_FAILED, 'Failed'),
    )

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="UUID primary key — prevents ID enumeration attacks.",
    )
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='ai_request_logs',
        help_text="The tenant organization that owns this AI request log.",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ai_request_logs',
        help_text="The user who initiated this AI generation request.",
    )
    task_id = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Celery background task ID for asynchronous execution tracking.",
    )
    prompt = models.TextField(
        help_text="Input text prompt sent to the LLM.",
    )
    response = models.JSONField(
        null=True,
        blank=True,
        help_text="Structured JSON output returned by the LLM upon completion.",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
        help_text="Current lifecycle state of the background task.",
    )
    error_message = models.TextField(
        null=True,
        blank=True,
        help_text="Sanitized error details if execution failed.",
    )
    tokens_used = models.IntegerField(
        default=0,
        help_text="Total tokens consumed (prompt + completion tokens).",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the request log entry was created.",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when the record was last updated.",
    )

    class Meta:
        verbose_name = 'AI Request Log'
        verbose_name_plural = 'AI Request Logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'task_id'], name='ailog_org_task_idx'),
            models.Index(fields=['organization', 'status'], name='ailog_org_status_idx'),
            models.Index(fields=['task_id'], name='ailog_task_id_idx'),
        ]

    def __str__(self) -> str:
        return f"AI Request [{self.task_id[:8]}...] - {self.organization.name} ({self.status})"
