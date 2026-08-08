from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model

User = get_user_model()
STRONG_PASSWORD = 'SecurePass123!@#'

# Disable throttling for the entire authentication test module.
# The login endpoint tests deliberately test the real endpoint,
# but we disable throttling so rates don't leak between tests.
override_no_throttle = override_settings(
    REST_FRAMEWORK={
        'DEFAULT_AUTHENTICATION_CLASSES': [
            'rest_framework_simplejwt.authentication.JWTAuthentication',
        ],
        'DEFAULT_PERMISSION_CLASSES': [
            'rest_framework.permissions.IsAuthenticated',
        ],
        'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
        'PAGE_SIZE': 20,
        'DEFAULT_THROTTLE_CLASSES': [],
        'DEFAULT_THROTTLE_RATES': {},
        'DEFAULT_RENDERER_CLASSES': ['rest_framework.renderers.JSONRenderer'],
    }
)


@override_no_throttle
class RegisterViewTests(APITestCase):
    url = '/api/v1/auth/register/'

    def test_successful_registration(self):
        data = {
            'email': 'newuser@example.com',
            'password': STRONG_PASSWORD,
            'first_name': 'John',
            'last_name': 'Doe',
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['email'], 'newuser@example.com')
        self.assertNotIn('password', response.data)
        self.assertTrue(User.objects.filter(email='newuser@example.com').exists())

    def test_duplicate_email_returns_400(self):
        User.objects.create_user(email='dup@example.com', password=STRONG_PASSWORD)
        response = self.client.post(self.url, {
            'email': 'dup@example.com',
            'password': STRONG_PASSWORD,
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_weak_password_rejected(self):
        response = self.client.post(self.url, {
            'email': 'weak@example.com',
            'password': 'short',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)

    def test_password_not_in_response(self):
        response = self.client.post(self.url, {
            'email': 'safe@example.com',
            'password': STRONG_PASSWORD,
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertNotIn('password', response.data)

    def test_missing_email_returns_400(self):
        response = self.client.post(self.url, {'password': STRONG_PASSWORD})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_password_returns_400(self):
        response = self.client.post(self.url, {'email': 'nopw@example.com'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


@override_no_throttle
class LoginViewTests(APITestCase):
    url = '/api/v1/auth/login/'

    def setUp(self):
        self.user = User.objects.create_user(
            email='login@example.com',
            password=STRONG_PASSWORD,
        )

    def test_successful_login_returns_tokens(self):
        response = self.client.post(self.url, {
            'email': 'login@example.com',
            'password': STRONG_PASSWORD,
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_wrong_password_returns_401(self):
        response = self.client.post(self.url, {
            'email': 'login@example.com',
            'password': 'wrongpassword',
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_nonexistent_user_returns_401(self):
        response = self.client.post(self.url, {
            'email': 'ghost@example.com',
            'password': STRONG_PASSWORD,
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


@override_no_throttle
class TokenRefreshViewTests(APITestCase):
    url = '/api/v1/auth/refresh/'

    def setUp(self):
        self.user = User.objects.create_user(
            email='refresh@example.com',
            password=STRONG_PASSWORD,
        )
        # Use direct JWT generation to avoid throttle in setUp
        self.refresh_token = str(RefreshToken.for_user(self.user))

    def test_refresh_returns_new_access_token(self):
        response = self.client.post(self.url, {'refresh': self.refresh_token})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_invalid_refresh_token_returns_401(self):
        response = self.client.post(self.url, {'refresh': 'invalid.token.here'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


@override_no_throttle
class ProfileViewTests(APITestCase):
    url = '/api/v1/auth/me/'

    def setUp(self):
        self.user = User.objects.create_user(
            email='me@example.com',
            password=STRONG_PASSWORD,
            first_name='Jane',
            last_name='Smith',
        )
        # Use direct JWT generation to avoid throttle in setUp
        token = RefreshToken.for_user(self.user)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {str(token.access_token)}"
        )

    def test_get_profile_returns_user_data(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'me@example.com')
        self.assertEqual(response.data['first_name'], 'Jane')
        self.assertNotIn('password', response.data)
        self.assertNotIn('last_login_ip', response.data)

    def test_unauthenticated_request_returns_401(self):
        self.client.credentials()  # clear auth
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_patch_updates_name(self):
        response = self.client.patch(self.url, {'first_name': 'Updated'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Updated')

    def test_patch_cannot_change_email(self):
        """Email changes require a dedicated verified flow — not allowed here."""
        response = self.client.patch(self.url, {'email': 'hacked@evil.com'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'me@example.com')  # unchanged
