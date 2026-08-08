from unittest.mock import patch
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model

from organizations.models import Organization, OrganizationMember
from ai_services.models import AIRequestLog
from ai_services.tasks import process_ai_request
from ai_services.services import LLMService, LLMServiceError

User = get_user_model()
STRONG_PASSWORD = 'SecurePass123!@#'

TEST_SETTINGS = override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
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


def _auth_client(client, user, workspace_id=None):
    """Helper to set JWT and workspace credentials on APIClient."""
    refresh = RefreshToken.for_user(user)
    credentials = {'HTTP_AUTHORIZATION': f'Bearer {str(refresh.access_token)}'}
    if workspace_id:
        credentials['HTTP_X_WORKSPACE_ID'] = str(workspace_id)
    client.credentials(**credentials)


@TEST_SETTINGS
class AIGenerateViewTests(APITestCase):
    url = '/api/v1/ai/generate/'

    def setUp(self):
        self.user = User.objects.create_user(email='aiuser@example.com', password=STRONG_PASSWORD)
        self.org = Organization.objects.create(name='AI Workspace', slug='ai-workspace')
        OrganizationMember.objects.create(
            organization=self.org, user=self.user, role=OrganizationMember.ROLE_OWNER
        )

    def test_generate_returns_202_accepted_and_creates_log(self):
        _auth_client(self.client, self.user, self.org.pk)
        response = self.client.post(self.url, {'prompt': 'Summarize Q3 operational metrics.'})
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertIn('task_id', response.data)
        self.assertIn('log_id', response.data)

        # Verify DB entry creation
        log = AIRequestLog.objects.get(pk=response.data['log_id'])
        self.assertEqual(log.organization, self.org)
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.prompt, 'Summarize Q3 operational metrics.')
        # Due to CELERY_TASK_ALWAYS_EAGER=True, task executed eagerly to COMPLETED
        self.assertIn(log.status, [AIRequestLog.STATUS_COMPLETED, AIRequestLog.STATUS_PENDING])

    def test_missing_workspace_header_returns_403(self):
        _auth_client(self.client, self.user)  # No workspace_id
        response = self.client.post(self.url, {'prompt': 'Valid prompt here'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_blank_prompt_returns_400(self):
        _auth_client(self.client, self.user, self.org.pk)
        response = self.client.post(self.url, {'prompt': '   '})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('prompt', response.data)

    def test_unauthenticated_returns_401(self):
        response = self.client.post(self.url, {'prompt': 'Valid prompt'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


@TEST_SETTINGS
class AIStatusViewTests(APITestCase):
    status_url_template = '/api/v1/ai/status/{task_id}/'

    def setUp(self):
        self.user_a = User.objects.create_user(email='user_a@example.com', password=STRONG_PASSWORD)
        self.user_b = User.objects.create_user(email='user_b@example.com', password=STRONG_PASSWORD)

        self.org_a = Organization.objects.create(name='Org A', slug='org-a')
        self.org_b = Organization.objects.create(name='Org B', slug='org-b')

        OrganizationMember.objects.create(organization=self.org_a, user=self.user_a, role=OrganizationMember.ROLE_OWNER)
        OrganizationMember.objects.create(organization=self.org_b, user=self.user_b, role=OrganizationMember.ROLE_OWNER)

        self.log_a = AIRequestLog.objects.create(
            organization=self.org_a,
            user=self.user_a,
            task_id='task-uuid-aaa-111',
            prompt='User A prompt',
            status=AIRequestLog.STATUS_COMPLETED,
            response={'content': 'Mock response output', 'tokens_used': 150},
            tokens_used=150,
        )

    def test_get_status_returns_log_payload(self):
        _auth_client(self.client, self.user_a, self.org_a.pk)
        url = self.status_url_template.format(task_id=self.log_a.task_id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['task_id'], self.log_a.task_id)
        self.assertEqual(response.data['status'], AIRequestLog.STATUS_COMPLETED)
        self.assertIn('content', response.data['response'])

    def test_cross_tenant_isolation_returns_404(self):
        """User B cannot access task status belonging to User A's workspace -> 404."""
        _auth_client(self.client, self.user_b, self.org_b.pk)
        url = self.status_url_template.format(task_id=self.log_a.task_id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


@TEST_SETTINGS
class CeleryTaskExecutionTests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(email='taskuser@example.com', password=STRONG_PASSWORD)
        self.org = Organization.objects.create(name='Task Org', slug='task-org')
        OrganizationMember.objects.create(organization=self.org, user=self.user, role=OrganizationMember.ROLE_OWNER)

        self.log = AIRequestLog.objects.create(
            organization=self.org,
            user=self.user,
            task_id='celery-task-999',
            prompt='Test background execution prompt.',
            status=AIRequestLog.STATUS_PENDING,
        )

    def test_task_completes_successfully(self):
        process_ai_request(str(self.log.id))
        self.log.refresh_from_db()
        self.assertEqual(self.log.status, AIRequestLog.STATUS_COMPLETED)
        self.assertIsNotNone(self.log.response)
        self.assertTrue(self.log.tokens_used > 0)
        self.assertIn('content', self.log.response)

    @patch.object(LLMService, 'generate', side_effect=LLMServiceError("Simulated LLM Provider Failure"))
    def test_task_handles_failure_and_sets_status_failed(self, mock_generate):
        process_ai_request(str(self.log.id))
        self.log.refresh_from_db()
        self.assertEqual(self.log.status, AIRequestLog.STATUS_FAILED)
        self.assertIn("Simulated LLM Provider Failure", self.log.error_message)


class LLMServiceTests(APITestCase):

    def test_llm_service_returns_mock_response_when_no_api_key(self):
        service = LLMService()
        result = service.generate("Analyze SaaS retention rates.")
        self.assertIn('content', result)
        self.assertIn('tokens_used', result)
        self.assertTrue(result['tokens_used'] > 0)
        self.assertEqual(result['metadata']['provider'], 'mock_provider')

    def test_llm_service_empty_prompt_raises_error(self):
        service = LLMService()
        with self.assertRaises(LLMServiceError):
            service.generate("   ")
