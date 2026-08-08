from django.contrib.auth.hashers import check_password
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model

from organizations.models import Organization, OrganizationMember
from billing.models import APIKey

User = get_user_model()
STRONG_PASSWORD = 'SecurePass123!@#'
KEYS_URL = '/api/v1/billing/keys/'


def _jwt_auth(client, user, workspace_id=None):
    """
    Set JWT credentials without hitting the login endpoint.
    Bypasses throttle limits for predictable test isolation.
    """
    refresh = RefreshToken.for_user(user)
    credentials = {'HTTP_AUTHORIZATION': f'Bearer {str(refresh.access_token)}'}
    if workspace_id:
        credentials['HTTP_X_WORKSPACE_ID'] = str(workspace_id)
    client.credentials(**credentials)


class APIKeyLifecycleTests(APITestCase):
    """
    Tests covering the full APIKey lifecycle:
    create → list (no raw key) → revoke → already-revoked guard.
    """

    def setUp(self):
        self.owner = User.objects.create_user(email='keyowner@example.com', password=STRONG_PASSWORD)
        self.member = User.objects.create_user(email='keymember@example.com', password=STRONG_PASSWORD)

        self.org = Organization.objects.create(name='Key Org', slug='key-org')
        OrganizationMember.objects.create(
            organization=self.org, user=self.owner, role=OrganizationMember.ROLE_OWNER
        )
        OrganizationMember.objects.create(
            organization=self.org, user=self.member, role=OrganizationMember.ROLE_MEMBER
        )

    def test_create_returns_raw_key_once(self):
        """POST must return the raw key in the response body."""
        _jwt_auth(self.client, self.owner, workspace_id=self.org.pk)
        response = self.client.post(KEYS_URL, {'name': 'Production Key'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('raw_key', response.data)
        self.assertIsNotNone(response.data['raw_key'])
        self.assertTrue(len(response.data['raw_key']) > 20)

    def test_raw_key_not_exposed_on_list(self):
        """GET list must never include the raw key or hashed_key."""
        _jwt_auth(self.client, self.owner, workspace_id=self.org.pk)
        self.client.post(KEYS_URL, {'name': 'Leak Test Key'})
        response = self.client.get(KEYS_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for key_data in response.data:
            self.assertNotIn('raw_key', key_data)
            self.assertNotIn('hashed_key', key_data)

    def test_raw_key_verifies_against_stored_hash(self):
        """The returned raw key must verify correctly with check_password."""
        _jwt_auth(self.client, self.owner, workspace_id=self.org.pk)
        response = self.client.post(KEYS_URL, {'name': 'Verify Key'})
        raw_key = response.data['raw_key']
        db_key = APIKey.objects.get(pk=response.data['id'])
        self.assertTrue(check_password(raw_key, db_key.hashed_key))

    def test_verify_method_returns_true_for_correct_key(self):
        _jwt_auth(self.client, self.owner, workspace_id=self.org.pk)
        response = self.client.post(KEYS_URL, {'name': 'Verify Method Key'})
        raw_key = response.data['raw_key']
        db_key = APIKey.objects.get(pk=response.data['id'])
        self.assertTrue(db_key.verify(raw_key))

    def test_verify_method_returns_false_for_wrong_key(self):
        _jwt_auth(self.client, self.owner, workspace_id=self.org.pk)
        response = self.client.post(KEYS_URL, {'name': 'Wrong Key Test'})
        db_key = APIKey.objects.get(pk=response.data['id'])
        self.assertFalse(db_key.verify('completely-wrong-key-value'))

    def test_prefix_is_first_8_chars_of_raw_key(self):
        _jwt_auth(self.client, self.owner, workspace_id=self.org.pk)
        response = self.client.post(KEYS_URL, {'name': 'Prefix Test'})
        raw_key = response.data['raw_key']
        self.assertEqual(response.data['prefix'], raw_key[:8])

    def test_revoke_soft_deletes_key(self):
        """DELETE sets is_active=False, does not hard-delete the record."""
        _jwt_auth(self.client, self.owner, workspace_id=self.org.pk)
        create_response = self.client.post(KEYS_URL, {'name': 'Revoke Me'})
        key_id = create_response.data['id']

        revoke_response = self.client.delete(f'{KEYS_URL}{key_id}/')
        self.assertEqual(revoke_response.status_code, status.HTTP_204_NO_CONTENT)

        db_key = APIKey.objects.get(pk=key_id)
        self.assertFalse(db_key.is_active)                             # soft-deleted
        self.assertTrue(APIKey.objects.filter(pk=key_id).exists())     # record preserved

    def test_verify_returns_false_for_revoked_key(self):
        """A revoked key must fail verification even with the correct raw value."""
        _jwt_auth(self.client, self.owner, workspace_id=self.org.pk)
        create_response = self.client.post(KEYS_URL, {'name': 'Revoke Verify'})
        raw_key = create_response.data['raw_key']
        key_id = create_response.data['id']
        self.client.delete(f'{KEYS_URL}{key_id}/')

        db_key = APIKey.objects.get(pk=key_id)
        self.assertFalse(db_key.verify(raw_key))

    def test_double_revoke_returns_400(self):
        _jwt_auth(self.client, self.owner, workspace_id=self.org.pk)
        create_response = self.client.post(KEYS_URL, {'name': 'Double Revoke'})
        key_id = create_response.data['id']
        self.client.delete(f'{KEYS_URL}{key_id}/')
        response = self.client.delete(f'{KEYS_URL}{key_id}/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_scoped_to_tenant(self):
        """Keys from another org must not appear in the list."""
        other_org = Organization.objects.create(name='Other Org', slug='other-org-keys')
        APIKey.objects.create_key(organization=other_org, name='Other Org Key')

        _jwt_auth(self.client, self.owner, workspace_id=self.org.pk)
        self.client.post(KEYS_URL, {'name': 'My Key'})
        response = self.client.get(KEYS_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for key_data in response.data:
            db_key = APIKey.objects.get(pk=key_data['id'])
            self.assertEqual(db_key.organization, self.org)


class APIKeyRBACTests(APITestCase):
    """
    RBAC enforcement: only admin/owner may create or revoke keys.
    """

    def setUp(self):
        self.owner = User.objects.create_user(email='rbacowner@example.com', password=STRONG_PASSWORD)
        self.member = User.objects.create_user(email='rbacmember@example.com', password=STRONG_PASSWORD)

        self.org = Organization.objects.create(name='RBAC Org', slug='rbac-org')
        OrganizationMember.objects.create(
            organization=self.org, user=self.owner, role=OrganizationMember.ROLE_OWNER
        )
        OrganizationMember.objects.create(
            organization=self.org, user=self.member, role=OrganizationMember.ROLE_MEMBER
        )

    def test_member_cannot_create_key(self):
        _jwt_auth(self.client, self.member, workspace_id=self.org.pk)
        response = self.client.post(KEYS_URL, {'name': 'Unauthorized Key'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_member_cannot_revoke_key(self):
        # Owner creates key first
        _jwt_auth(self.client, self.owner, workspace_id=self.org.pk)
        create_response = self.client.post(KEYS_URL, {'name': 'Owner Key'})
        key_id = create_response.data['id']

        # Member attempts to revoke
        _jwt_auth(self.client, self.member, workspace_id=self.org.pk)
        response = self.client.delete(f'{KEYS_URL}{key_id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_no_workspace_header_returns_403(self):
        """Without X-Workspace-ID, IsWorkspaceAdminOrOwner denies all access."""
        _jwt_auth(self.client, self.owner)  # no workspace_id
        response = self.client.post(KEYS_URL, {'name': 'No Header Key'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_returns_401(self):
        response = self.client.get(KEYS_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
