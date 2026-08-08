import uuid
import logging
from django.db import models
from django.conf import settings

logger = logging.getLogger(__name__)


class Organization(models.Model):
    """
    Represents a tenant (workspace) in the multi-tenant SaaS architecture.

    Security design decisions:
    - UUID primary key: prevents sequential ID enumeration.
    - slug: human-readable identifier — unique and URL-safe.
    - is_active: soft-delete / suspension mechanism without data loss.
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="UUID primary key — prevents tenant ID enumeration.",
    )
    name = models.CharField(max_length=255)
    slug = models.SlugField(
        unique=True,
        max_length=255,
        help_text="URL-safe unique identifier for this organization.",
    )
    is_active = models.BooleanField(
        default=True,
        help_text=(
            "Inactive organizations are suspended — all workspace header "
            "access attempts return 403 regardless of membership."
        ),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Organization'
        verbose_name_plural = 'Organizations'
        ordering = ['name']
        indexes = [
            models.Index(fields=['slug'], name='org_slug_idx'),
            models.Index(fields=['is_active'], name='org_is_active_idx'),
        ]

    def __str__(self) -> str:
        return self.name


class OrganizationMember(models.Model):
    """
    Links a User to an Organization with a specific RBAC role.

    Security design decisions:
    - unique_together ensures one membership record per (org, user) pair.
    - is_active on membership: allows revoking workspace access without
      removing the membership record (preserves audit history).
    - Middleware filters on BOTH membership.is_active AND organization.is_active.
    """
    ROLE_OWNER = 'owner'
    ROLE_ADMIN = 'admin'
    ROLE_MEMBER = 'member'

    ROLE_CHOICES = (
        (ROLE_OWNER, 'Owner'),
        (ROLE_ADMIN, 'Admin'),
        (ROLE_MEMBER, 'Member'),
    )

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='members',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='organization_memberships',
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_MEMBER,
        db_index=True,
    )
    is_active = models.BooleanField(
        default=True,
        help_text=(
            "Deactivate to suspend this user's access to the workspace "
            "without revoking the membership record (preserves audit history)."
        ),
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Organization Member'
        verbose_name_plural = 'Organization Members'
        unique_together = ('organization', 'user')
        indexes = [
            models.Index(fields=['organization', 'user'], name='member_org_user_idx'),
            models.Index(fields=['role'], name='member_role_idx'),
            models.Index(fields=['is_active'], name='member_is_active_idx'),
        ]

    def __str__(self) -> str:
        return f"{self.user.email} — {self.organization.name} ({self.get_role_display()})"
