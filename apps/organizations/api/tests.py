from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model

from organizations.models import Organization, OrganizationMember

User = get_user_model()
STRONG_PASSWORD = 'SecurePass123!@#'


def _jwt_auth(client, user, workspace_id=None):
    """
    Set JWT credentials on the test client without going through the login endpoint.
    This bypasses throttle limits, making tests fast and deterministic.
    Optionally attach X-Workspace-ID header.
    """
    refresh = RefreshToken.for_user(user)
    credentials = {'HTTP_AUTHORIZATION': f'Bearer {str(refresh.access_token)}'}
    if workspace_id:
        credentials['HTTP_X_WORKSPACE_ID'] = str(workspace_id)
    client.credentials(**credentials)


class OrganizationViewSetTests(APITestCase):
    url = '/api/v1/workspaces/'

    def setUp(self):
        self.user_a = User.objects.create_user(email='usera@example.com', password=STRONG_PASSWORD)
        self.user_b = User.objects.create_user(email='userb@example.com', password=STRONG_PASSWORD)

    def test_create_workspace_makes_user_owner(self):
        _jwt_auth(self.client, self.user_a)
        response = self.client.post(self.url, {'name': 'Alpha Corp'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        org = Organization.objects.get(pk=response.data['id'])
        self.assertTrue(
            OrganizationMember.objects.filter(
                organization=org,
                user=self.user_a,
                role=OrganizationMember.ROLE_OWNER,
            ).exists()
        )

    def test_slug_auto_generated(self):
        _jwt_auth(self.client, self.user_a)
        response = self.client.post(self.url, {'name': 'My Great Company'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['slug'], 'my-great-company')

    def test_slug_collision_resolved(self):
        _jwt_auth(self.client, self.user_a)
        self.client.post(self.url, {'name': 'Beta Corp'})
        response = self.client.post(self.url, {'name': 'Beta Corp'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['slug'], 'beta-corp-1')

    def test_list_returns_only_users_own_workspaces(self):
        """Tenant isolation: user can only list their own workspaces."""
        _jwt_auth(self.client, self.user_a)
        self.client.post(self.url, {'name': 'User A Workspace'})

        # Create workspace for user B (independent)
        org_b = Organization.objects.create(name='User B Only', slug='user-b-only')
        OrganizationMember.objects.create(
            organization=org_b, user=self.user_b, role=OrganizationMember.ROLE_OWNER
        )

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [w['id'] for w in response.data['results']]
        self.assertNotIn(str(org_b.pk), ids)

    def test_unauthenticated_request_returns_401(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TenantIsolationTests(APITestCase):
    """
    Cross-tenant data isolation tests.
    These verify that a user cannot access another user's workspace
    even if they know the workspace UUID.
    """

    def setUp(self):
        self.user_a = User.objects.create_user(email='isoa@example.com', password=STRONG_PASSWORD)
        self.user_b = User.objects.create_user(email='isob@example.com', password=STRONG_PASSWORD)

        # Org owned by user B — user A has no membership
        self.org_b = Organization.objects.create(name='B Corp', slug='b-corp-iso')
        OrganizationMember.objects.create(
            organization=self.org_b,
            user=self.user_b,
            role=OrganizationMember.ROLE_OWNER,
        )

    def test_user_a_cannot_access_user_b_workspace_via_header(self):
        """User A sending X-Workspace-ID for User B's org must receive 403."""
        _jwt_auth(self.client, self.user_a, workspace_id=self.org_b.pk)
        response = self.client.get('/api/v1/workspaces/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_user_a_cannot_retrieve_user_b_workspace_detail(self):
        """Direct GET to another workspace's detail URL must return 404 (not in queryset)."""
        _jwt_auth(self.client, self.user_a)
        response = self.client.get(f'/api/v1/workspaces/{self.org_b.pk}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_a_cannot_list_user_b_members(self):
        """Member list endpoint with user B's workspace ID must return 403."""
        _jwt_auth(self.client, self.user_a, workspace_id=self.org_b.pk)
        response = self.client.get(f'/api/v1/workspaces/{self.org_b.pk}/members/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class OrganizationMemberViewSetTests(APITestCase):
    member_list_url_template = '/api/v1/workspaces/{org_id}/members/'

    def setUp(self):
        self.owner = User.objects.create_user(email='owner@example.com', password=STRONG_PASSWORD)
        self.admin = User.objects.create_user(email='admin@example.com', password=STRONG_PASSWORD)
        self.regular = User.objects.create_user(email='regular@example.com', password=STRONG_PASSWORD)
        self.outsider = User.objects.create_user(email='outsider@example.com', password=STRONG_PASSWORD)
        self.invitee = User.objects.create_user(email='invitee@example.com', password=STRONG_PASSWORD)

        self.org = Organization.objects.create(name='Test Org', slug='test-org-members')
        self.owner_membership = OrganizationMember.objects.create(
            organization=self.org, user=self.owner, role=OrganizationMember.ROLE_OWNER
        )
        self.admin_membership = OrganizationMember.objects.create(
            organization=self.org, user=self.admin, role=OrganizationMember.ROLE_ADMIN
        )
        self.regular_membership = OrganizationMember.objects.create(
            organization=self.org, user=self.regular, role=OrganizationMember.ROLE_MEMBER
        )
        self.list_url = self.member_list_url_template.format(org_id=self.org.pk)

    def _auth_as(self, user):
        _jwt_auth(self.client, user, workspace_id=self.org.pk)

    def test_owner_can_list_members(self):
        self._auth_as(self.owner)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 3)

    def test_owner_can_add_member(self):
        self._auth_as(self.owner)
        response = self.client.post(self.list_url, {
            'email': 'invitee@example.com',
            'role': 'member',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            OrganizationMember.objects.filter(
                organization=self.org, user=self.invitee
            ).exists()
        )

    def test_admin_can_add_member(self):
        self._auth_as(self.admin)
        response = self.client.post(self.list_url, {
            'email': 'invitee@example.com',
            'role': 'member',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_regular_member_cannot_add_member(self):
        """RBAC: regular member must receive 403 when trying to add members."""
        self._auth_as(self.regular)
        response = self.client.post(self.list_url, {
            'email': 'invitee@example.com',
            'role': 'member',
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_duplicate_member_add_returns_400(self):
        self._auth_as(self.owner)
        response = self.client.post(self.list_url, {
            'email': 'regular@example.com',
            'role': 'member',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_nonexistent_user_add_returns_400(self):
        self._auth_as(self.owner)
        response = self.client.post(self.list_url, {
            'email': 'ghost@nowhere.com',
            'role': 'member',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_owner_can_remove_member(self):
        self._auth_as(self.owner)
        detail_url = f'{self.list_url}{self.regular_membership.pk}/'
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            OrganizationMember.objects.filter(pk=self.regular_membership.pk).exists()
        )

    def test_owner_cannot_remove_themselves(self):
        self._auth_as(self.owner)
        detail_url = f'{self.list_url}{self.owner_membership.pk}/'
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_regular_member_cannot_remove_member(self):
        self._auth_as(self.regular)
        detail_url = f'{self.list_url}{self.admin_membership.pk}/'
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
