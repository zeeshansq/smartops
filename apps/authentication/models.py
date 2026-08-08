import uuid
import logging
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils import timezone

logger = logging.getLogger(__name__)


class CustomUserManager(BaseUserManager):
    """
    Custom manager for the User model that uses email as the unique identifier
    instead of a username field.
    """

    def create_user(self, email: str, password: str | None = None, **extra_fields) -> 'User':
        """
        Create and persist a regular user.

        Args:
            email:        The user's email address (used as the login identifier).
            password:     Plain-text password. If not provided, an unusable password is set.
            extra_fields: Additional field values to pass to the User model.

        Raises:
            ValueError: If email is empty or falsy.
        """
        if not email:
            raise ValueError("The Email field must be set.")

        email = self.normalize_email(email)
        extra_fields.setdefault('is_active', True)
        user = self.model(email=email, **extra_fields)

        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()

        user.full_clean()   # Run model-level validation before saving
        user.save(using=self._db)

        logger.info("User created: %s", email)
        return user

    def create_superuser(self, email: str, password: str | None = None, **extra_fields) -> 'User':
        """
        Create and persist a superuser (staff + superuser privileges).

        Raises:
            ValueError: If is_staff or is_superuser are explicitly set to False.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_email_verified', True)  # Superusers are pre-verified

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model using email as the primary authentication identifier.

    Security design decisions:
    - UUID primary key: prevents ID enumeration attacks.
    - Email is indexed: fast lookups without exposing sequential IDs.
    - is_email_verified: prevents use of unverified accounts in sensitive flows.
    - last_login_ip: supports audit logging and anomalous-login detection.
    - full_clean() called by manager: enforces model validation on creation.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="UUID primary key — prevents ID enumeration attacks.",
    )
    email = models.EmailField(
        unique=True,
        db_index=True,
        help_text="Used as the unique login identifier.",
    )
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    is_staff = models.BooleanField(
        default=False,
        help_text="Designates whether the user can access the Django admin site.",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Uncheck to deactivate the account without deleting it.",
    )
    is_email_verified = models.BooleanField(
        default=False,
        help_text="Set to True once the user has verified their email address.",
    )
    last_login_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        protocol='both',
        unpack_ipv4=True,
        help_text="IP address of the user's most recent login — used for audit logging.",
    )
    date_joined = models.DateTimeField(
        default=timezone.now,
        help_text="Timestamp of account creation.",
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        indexes = [
            models.Index(fields=['email'], name='user_email_idx'),
            models.Index(fields=['is_active', 'is_email_verified'], name='user_active_verified_idx'),
        ]

    def __str__(self) -> str:
        return self.email

    def get_full_name(self) -> str:
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name or self.email

    def get_short_name(self) -> str:
        return self.first_name or self.email
