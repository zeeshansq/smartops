import logging
from rest_framework import views, generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ai_services.models import AIRequestLog
from ai_services.tasks import process_ai_request
from .serializers import AIGenerateSerializer, AIRequestLogSerializer

logger = logging.getLogger(__name__)


class AIGenerateView(views.APIView):
    """
    POST /api/v1/ai/generate/

    Initiates an asynchronous AI generation request.

    Tenant Isolation & Middleware Rules:
    - Requires X-Workspace-ID header (enforced by TenantMiddleware).
    - Requires authenticated user belonging to the workspace.
    - Creates an AIRequestLog entry in 'PENDING' status linked to request.tenant.
    - Offloads task execution to Celery background worker without blocking the HTTP request.
    - Returns HTTP 202 Accepted with task_id and log_id.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response(
                {'detail': 'X-Workspace-ID header is required.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = AIGenerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        prompt = serializer.validated_data['prompt']

        # 1. Create initial log entry in PENDING state
        log = AIRequestLog.objects.create(
            organization=tenant,
            user=request.user,
            prompt=prompt,
            status=AIRequestLog.STATUS_PENDING,
            task_id='',  # Temporary placeholder until delay() returns task_id
        )

        # 2. Dispatch async Celery task
        async_task = process_ai_request.delay(str(log.id))

        # 3. Save actual Celery task_id on record
        log.task_id = async_task.id
        log.save(update_fields=['task_id'])

        logger.info(
            "AI generation request queued: task_id=%s, log_id=%s, workspace=%s, user=%s",
            async_task.id,
            log.id,
            tenant.name,
            request.user.email,
        )

        return Response(
            {
                "task_id": log.task_id,
                "log_id": str(log.id),
                "status": log.status,
            },
            status=status.HTTP_202_ACCEPTED,
        )


class AIStatusView(generics.RetrieveAPIView):
    """
    GET /api/v1/ai/status/<task_id>/

    Retrieves status and output payload for an asynchronous AI request task.

    Security & Cross-Tenant Data Isolation:
    - Requires X-Workspace-ID header.
    - `get_queryset()` strictly filters records by `organization=request.tenant`.
    - If User A queries a task_id belonging to User B's workspace, the record will not be found,
      returning HTTP 404 Not Found to prevent task ID enumeration and cross-tenant data leakage.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = AIRequestLogSerializer
    lookup_field = 'task_id'

    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return AIRequestLog.objects.none()
        return AIRequestLog.objects.filter(organization=tenant)

    def retrieve(self, request, *args, **kwargs):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response(
                {'detail': 'X-Workspace-ID header is required.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        return super().retrieve(request, *args, **kwargs)
