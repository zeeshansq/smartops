import uuid
import secrets
import logging
from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from django.conf import settings

logger = logging.getLogger(__name__)


class APIKeyManager(models.Manager):
    """
    Manager providing secure key generation and verification helpers.
    """

    def create_key(self, organization, name: str) -> tuple['APIKey', str]:
        """
        Generate a cryptographically secure API key, hash it, and persist the record.

        Returns:
            A (APIKey instance, raw_key string) tuple.
            The raw_key is returned ONCE at creation and is never stored or
            re-derivable. The caller must present it to the user immediately.

        Security:
        - `secrets.token_urlsafe(32)` generates 256-bit entropy — safe for API keys.
        - Only the first 8 characters (prefix) are stored in plain text for display.
        - The full key is hashed with Django's `make_password()` (PBKDF2-SHA256).
        """
        raw_key = secrets.token_urlsafe(32)
        prefix = raw_key[:8]
        hashed = make_password(raw_key)

        instance = self.model(
            organization=organization,
            name=name,
            prefix=prefix,
            hashed_key=hashed,
        )
        instance.save(using=self._db)

        logger.info(
            "API key '%s' (prefix=%s) created for org '%s'",
            name,
            prefix,
            organization.name,
        )
        return instance, raw_key


class APIKey(models.Model):
    """
    Represents a long-lived programmatic API key scoped to an Organization.

    Security design decisions:
    - Only the key PREFIX (8 chars) is stored in plain text — safe for display/identification.
    - The full key is hashed using Django's `make_password()` (PBKDF2-SHA256 by default).
    - The raw key is returned ONLY ONCE at creation via `APIKeyManager.create_key()`.
    - `is_active=False` is a soft revoke — record preserved for audit history.
    - `last_used_at` is updated on every authenticated request for usage auditing.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='api_keys',
    )
    name = models.CharField(
        max_length=100,
        help_text="Human-readable label, e.g. 'Production AI Integration'.",
    )
    prefix = models.CharField(
        max_length=8,
        help_text="First 8 characters of the raw key — safe for display and identification.",
        editable=False,
    )
    hashed_key = models.CharField(
        max_length=255,
        help_text="PBKDF2-SHA256 hash of the full raw key. Never store or display the raw key.",
        editable=False,
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Set to False to revoke the key without deleting the audit record.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Updated on each successful API key authentication.",
    )

    objects = APIKeyManager()

    class Meta:
        app_label = 'billing'
        verbose_name = 'API Key'
        verbose_name_plural = 'API Keys'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'is_active'], name='apikey_org_active_idx'),
        ]

    def __str__(self) -> str:
        status = 'active' if self.is_active else 'revoked'
        return f"{self.name} ({self.prefix}***) [{status}]"

    def verify(self, raw_key: str) -> bool:
        """
        Verify a candidate raw key against the stored hash.
        Returns False if the key is revoked, regardless of hash match.
        """
        if not self.is_active:
            return False
        return check_password(raw_key, self.hashed_key)
