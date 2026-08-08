import logging
from rest_framework import viewsets, status, mixins
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from billing.models import APIKey
from organizations.api.permissions import IsWorkspaceAdminOrOwner
from .serializers import APIKeySerializer, APIKeyCreateSerializer, APIKeyCreateResponseSerializer

logger = logging.getLogger(__name__)


class APIKeyViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    API Key management for programmatic access (e.g. AI integrations).
    Requires both authentication and admin/owner role in the current workspace.

    GET    /api/v1/billing/keys/       — List active keys (prefix only, no raw key).
    POST   /api/v1/billing/keys/       — Create a new key (raw key returned ONCE).
    DELETE /api/v1/billing/keys/{id}/  — Revoke (soft-delete) a key.

    Security:
    - All actions require X-Workspace-ID header (enforced by TenantMiddleware).
    - All actions require admin or owner role (IsWorkspaceAdminOrOwner).
    - Raw key is generated server-side and returned only in the POST response body.
    - Revocation is a soft-delete (is_active=False) to preserve audit history.
    - `hashed_key` is never serialized in any response.
    """

    permission_classes = [IsAuthenticated, IsWorkspaceAdminOrOwner]

    def get_queryset(self):
        """Scope to the current workspace. Returns none if no tenant context."""
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return APIKey.objects.none()
        return APIKey.objects.filter(organization=tenant).order_by('-created_at')

    def get_serializer_class(self):
        if self.action == 'create':
            return APIKeyCreateSerializer
        return APIKeySerializer

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = APIKeySerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """
        Generate a new API key.

        The raw key is returned exactly once in the response.
        It is NOT stored in plain text — only the PBKDF2 hash is persisted.
        Clients must store the raw key securely; it cannot be recovered.
        """
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response(
                {'detail': 'X-Workspace-ID header is required.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        create_serializer = APIKeyCreateSerializer(data=request.data)
        create_serializer.is_valid(raise_exception=True)

        api_key, raw_key = APIKey.objects.create_key(
            organization=tenant,
            name=create_serializer.validated_data['name'],
        )

        logger.info(
            "API key '%s' created for workspace '%s' by user %s",
            api_key.name,
            tenant.name,
            request.user.pk,
        )

        # Attach raw_key to the instance so the response serializer can include it.
        # This is the ONLY moment the raw key is exposed.
        api_key.raw_key = raw_key
        response_data = APIKeyCreateResponseSerializer(api_key).data

        return Response(response_data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        """
        Revoke an API key (soft-delete: set is_active=False).
        Preserves the record for audit history.
        """
        api_key = self.get_object()

        if not api_key.is_active:
            return Response(
                {'detail': 'This API key has already been revoked.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        api_key.is_active = False
        api_key.save(update_fields=['is_active'])

        logger.info(
            "API key '%s' (prefix=%s) revoked for workspace '%s' by user %s",
            api_key.name,
            api_key.prefix,
            api_key.organization.name,
            request.user.pk,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
