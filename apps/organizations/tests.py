import uuid
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.http import HttpResponse
from .models import Organization, OrganizationMember
from .middleware import TenantMiddleware

User = get_user_model()


class OrganizationModelTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(email="user@example.com", password="password123")
        self.org = Organization.objects.create(name="Acme Corp", slug="acme-corp")

    def test_organization_creation(self):
        self.assertEqual(self.org.name, "Acme Corp")
        self.assertTrue(self.org.is_active)
        self.assertIsNotNone(self.org.id)

    def test_organization_id_is_uuid(self):
        self.assertIsInstance(self.org.id, uuid.UUID)

    def test_organization_slug_is_unique(self):
        with self.assertRaises(Exception):
            Organization.objects.create(name="Acme Dup", slug="acme-corp")

    def test_organization_member_creation(self):
        member = OrganizationMember.objects.create(
            organization=self.org,
            user=self.user,
            role=OrganizationMember.ROLE_OWNER,
        )
        self.assertEqual(member.role, "owner")
        self.assertEqual(member.organization, self.org)
        self.assertEqual(member.user, self.user)
        self.assertTrue(member.is_active)   # New: default is_active=True

    def test_organization_member_is_active_defaults_true(self):
        member = OrganizationMember.objects.create(
            organization=self.org,
            user=self.user,
        )
        self.assertTrue(member.is_active)

    def test_unique_member_constraint(self):
        OrganizationMember.objects.create(
            organization=self.org,
            user=self.user,
            role=OrganizationMember.ROLE_MEMBER,
        )
        with self.assertRaises(IntegrityError):
            OrganizationMember.objects.create(
                organization=self.org,
                user=self.user,
                role=OrganizationMember.ROLE_ADMIN,
            )


class TenantMiddlewareTests(TestCase):

    def setUp(self):
        self.factory = RequestFactory()

        self.user = User.objects.create_user(email="tenantuser@example.com", password="password123")
        self.other_user = User.objects.create_user(email="otheruser@example.com", password="password123")
        self.inactive_user = User.objects.create_user(
            email="inactiveuser@example.com", password="password123", is_active=False
        )

        self.org = Organization.objects.create(name="Tech Corp", slug="tech-corp")
        self.inactive_org = Organization.objects.create(
            name="Inactive Corp", slug="inactive-corp", is_active=False
        )

        # Active membership for self.user
        self.membership = OrganizationMember.objects.create(
            organization=self.org,
            user=self.user,
            role=OrganizationMember.ROLE_ADMIN,
        )

        def dummy_get_response(request):
            return HttpResponse("OK")

        self.middleware = TenantMiddleware(dummy_get_response)

    # ── Pass-through ──────────────────────────────────────────────────────────

    def test_no_header_passes_through(self):
        request = self.factory.get('/')
        request.user = self.user
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(request.tenant)
        self.assertIsNone(request.tenant_role)

    # ── Happy path ────────────────────────────────────────────────────────────

    def test_valid_header_sets_tenant_and_role(self):
        request = self.factory.get('/', HTTP_X_WORKSPACE_ID=str(self.org.id))
        request.user = self.user
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(request.tenant, self.org)
        self.assertEqual(request.tenant_role, OrganizationMember.ROLE_ADMIN)

    # ── Authentication guard ──────────────────────────────────────────────────

    def test_unauthenticated_user_returns_403(self):
        from django.contrib.auth.models import AnonymousUser
        request = self.factory.get('/', HTTP_X_WORKSPACE_ID=str(self.org.id))
        request.user = AnonymousUser()
        response = self.middleware(request)
        self.assertEqual(response.status_code, 403)

    # ── Membership guard ──────────────────────────────────────────────────────

    def test_non_member_user_returns_403(self):
        request = self.factory.get('/', HTTP_X_WORKSPACE_ID=str(self.org.id))
        request.user = self.other_user
        response = self.middleware(request)
        self.assertEqual(response.status_code, 403)

    def test_inactive_organization_returns_403(self):
        # Even with valid membership, inactive org = denied
        OrganizationMember.objects.create(
            organization=self.inactive_org,
            user=self.user,
            role=OrganizationMember.ROLE_OWNER,
        )
        request = self.factory.get('/', HTTP_X_WORKSPACE_ID=str(self.inactive_org.id))
        request.user = self.user
        response = self.middleware(request)
        self.assertEqual(response.status_code, 403)

    def test_inactive_membership_returns_403(self):
        """New: deactivated membership (is_active=False) must be denied even if org is active."""
        self.membership.is_active = False
        self.membership.save()
        request = self.factory.get('/', HTTP_X_WORKSPACE_ID=str(self.org.id))
        request.user = self.user
        response = self.middleware(request)
        self.assertEqual(response.status_code, 403)

    def test_inactive_user_account_returns_403(self):
        """New: a deactivated user account must be denied even with a valid active membership."""
        OrganizationMember.objects.create(
            organization=self.org,
            user=self.inactive_user,
            role=OrganizationMember.ROLE_MEMBER,
        )
        request = self.factory.get('/', HTTP_X_WORKSPACE_ID=str(self.org.id))
        request.user = self.inactive_user
        response = self.middleware(request)
        self.assertEqual(response.status_code, 403)

    # ── Input validation ──────────────────────────────────────────────────────

    def test_malformed_uuid_returns_403(self):
        request = self.factory.get('/', HTTP_X_WORKSPACE_ID="not-a-uuid")
        request.user = self.user
        response = self.middleware(request)
        self.assertEqual(response.status_code, 403)

    def test_oversized_header_returns_403(self):
        """New: header value exceeding max length must be rejected before DB query."""
        oversized_id = "a" * 100
        request = self.factory.get('/', HTTP_X_WORKSPACE_ID=oversized_id)
        request.user = self.user
        response = self.middleware(request)
        self.assertEqual(response.status_code, 403)

    def test_nonexistent_uuid_returns_403(self):
        request = self.factory.get('/', HTTP_X_WORKSPACE_ID=str(uuid.uuid4()))
        request.user = self.user
        response = self.middleware(request)
        self.assertEqual(response.status_code, 403)

    def test_response_body_is_generic_on_403(self):
        """Uniform error response prevents information leakage."""
        import json
        request = self.factory.get('/', HTTP_X_WORKSPACE_ID=str(uuid.uuid4()))
        request.user = self.user
        response = self.middleware(request)
        self.assertEqual(response.status_code, 403)
        data = json.loads(response.content)
        self.assertIn('detail', data)
        self.assertEqual(data['detail'], "Access denied to the specified workspace.")
