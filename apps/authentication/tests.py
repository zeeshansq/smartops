from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()


class UserModelTests(TestCase):

    # ── Creation ─────────────────────────────────────────────────────────────

    def test_create_user_success(self):
        user = User.objects.create_user(email="test@example.com", password="SecurePassword123!")
        self.assertEqual(user.email, "test@example.com")
        self.assertTrue(user.check_password("SecurePassword123!"))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.is_active)
        self.assertIsNotNone(user.id)

    def test_create_user_sets_unusable_password_when_none_given(self):
        user = User.objects.create_user(email="nopw@example.com")
        self.assertFalse(user.has_usable_password())

    def test_create_user_without_email_raises_value_error(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email="", password="password123")

    def test_email_normalization(self):
        """Domain portion of email must be lowercased on save."""
        user = User.objects.create_user(email="TEST.USER@EXAMPLE.COM", password="SecurePassword123!")
        self.assertEqual(user.email, "TEST.USER@example.com")

    def test_duplicate_email_raises_integrity_error(self):
        from django.db import IntegrityError
        User.objects.create_user(email="dup@example.com", password="SecurePassword123!")
        with self.assertRaises(Exception):
            User.objects.create_user(email="dup@example.com", password="AnotherPass456!")

    # ── Superuser ─────────────────────────────────────────────────────────────

    def test_create_superuser(self):
        admin = User.objects.create_superuser(email="admin@example.com", password="AdminPassword123!")
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.is_active)
        self.assertTrue(admin.is_email_verified)   # Superusers are pre-verified

    def test_create_superuser_with_is_staff_false_raises_error(self):
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                email="bad@example.com",
                password="Password123!",
                is_staff=False,
            )

    def test_create_superuser_with_is_superuser_false_raises_error(self):
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                email="bad2@example.com",
                password="Password123!",
                is_superuser=False,
            )

    # ── New Security Fields ───────────────────────────────────────────────────

    def test_is_email_verified_defaults_to_false(self):
        user = User.objects.create_user(email="unverified@example.com", password="SecurePassword123!")
        self.assertFalse(user.is_email_verified)

    def test_last_login_ip_defaults_to_none(self):
        user = User.objects.create_user(email="ip@example.com", password="SecurePassword123!")
        self.assertIsNone(user.last_login_ip)

    def test_last_login_ip_accepts_ipv4(self):
        user = User.objects.create_user(email="ipv4@example.com", password="SecurePassword123!")
        user.last_login_ip = '192.168.1.1'
        user.save()
        user.refresh_from_db()
        self.assertEqual(user.last_login_ip, '192.168.1.1')

    def test_last_login_ip_accepts_ipv6(self):
        user = User.objects.create_user(email="ipv6@example.com", password="SecurePassword123!")
        user.last_login_ip = '2001:db8::1'
        user.save()
        user.refresh_from_db()
        self.assertEqual(user.last_login_ip, '2001:db8::1')

    # ── UUID Primary Key ──────────────────────────────────────────────────────

    def test_user_id_is_uuid(self):
        import uuid
        user = User.objects.create_user(email="uuid@example.com", password="SecurePassword123!")
        self.assertIsInstance(user.id, uuid.UUID)

    # ── Utility Methods ───────────────────────────────────────────────────────

    def test_get_full_name_returns_combined_name(self):
        user = User.objects.create_user(
            email="john@example.com",
            password="SecurePassword123!",
            first_name="John",
            last_name="Doe",
        )
        self.assertEqual(user.get_full_name(), "John Doe")

    def test_get_full_name_falls_back_to_email(self):
        user = User.objects.create_user(email="anon@example.com", password="SecurePassword123!")
        self.assertEqual(user.get_full_name(), "anon@example.com")

    def test_get_short_name_returns_first_name(self):
        user = User.objects.create_user(
            email="short@example.com",
            password="SecurePassword123!",
            first_name="Jane",
        )
        self.assertEqual(user.get_short_name(), "Jane")
