import uuid
import logging
from django.http import JsonResponse
from .models import OrganizationMember

logger = logging.getLogger(__name__)

# Guard against excessively long header values that could indicate an injection attempt
_MAX_WORKSPACE_ID_LENGTH = 36  # Standard UUID string length


class TenantMiddleware:
    """
    Middleware that resolves multi-tenant context from the X-Workspace-ID HTTP header.

    Security properties:
    - Only activates when the header is present (opt-in per request).
    - Authenticates the request using JWTAuthentication before any tenant lookup,
      ensuring JWT-authenticated API users are correctly identified (Django's session
      auth alone does not populate request.user for JWT-based requests at middleware time).
    - Rejects unauthenticated requests with 403.
    - Validates UUID format before any DB query (prevents injection / 500 leaks).
    - Guards header length to prevent oversized-value attacks.
    - Filters on organization.is_active AND member.is_active AND user.is_active.
    - Any unexpected DB error returns 403 (fail-closed), never a 500.
    - All denied access attempts are logged at WARNING level for SIEM ingestion.

    Sets on request (on success only):
        request.tenant       — The resolved Organization instance.
        request.tenant_role  — The member's role string ('owner'|'admin'|'member').
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def _resolve_user(self, request):
        """
        Return the authenticated user for this request, trying both:
        1. Django session auth (already populated by AuthenticationMiddleware).
        2. JWT Bearer token (resolved lazily by DRF — we invoke it eagerly here).

        Returns None if neither succeeds.
        """
        # Fast path: session-based auth already resolved this user
        if hasattr(request, 'user') and request.user.is_authenticated:
            return request.user

        # JWT path: attempt to authenticate via simplejwt
        try:
            from rest_framework_simplejwt.authentication import JWTAuthentication
            result = JWTAuthentication().authenticate(request)
            if result is not None:
                user, token = result
                # Populate request.user so downstream middleware/views see the right user
                request.user = user
                return user
        except Exception:
            pass

        return None

    def __call__(self, request):
        workspace_id = (
            request.headers.get('X-Workspace-ID')
            or request.META.get('HTTP_X_WORKSPACE_ID')
        )

        # Always initialize to None — safe defaults
        request.tenant = None
        request.tenant_role = None

        if not workspace_id:
            return self.get_response(request)

        # ── Guard 1: length check — prevents header stuffing / injection ────────
        if len(workspace_id) > _MAX_WORKSPACE_ID_LENGTH:
            logger.warning(
                "TenantMiddleware: oversized X-Workspace-ID header rejected "
                "(length=%d, path=%s)",
                len(workspace_id),
                request.path,
            )
            return self._deny()

        # ── Guard 2: authentication (session OR JWT) ────────────────────────────
        user = self._resolve_user(request)
        if not user or not user.is_authenticated:
            logger.warning(
                "TenantMiddleware: unauthenticated request with X-Workspace-ID "
                "header (path=%s)",
                request.path,
            )
            return self._deny()

        # ── Guard 3: UUID format validation — fail-safe, no 500 ────────────────
        try:
            valid_uuid = uuid.UUID(str(workspace_id))
        except (ValueError, TypeError, AttributeError):
            logger.warning(
                "TenantMiddleware: malformed X-Workspace-ID header rejected "
                "(user=%s, path=%s)",
                user.pk,
                request.path,
            )
            return self._deny()

        # ── Guard 4: active membership lookup ───────────────────────────────────
        # Filters on ALL three activity flags:
        #   organization.is_active  — org not suspended
        #   member.is_active        — membership not individually revoked
        #   user.is_active          — user account not deactivated
        try:
            membership = OrganizationMember.objects.select_related(
                'organization'
            ).get(
                organization__id=valid_uuid,
                organization__is_active=True,
                user=user,
                user__is_active=True,
                is_active=True,
            )
        except OrganizationMember.DoesNotExist:
            logger.warning(
                "TenantMiddleware: access denied to workspace %s for user %s (path=%s)",
                valid_uuid,
                user.pk,
                request.path,
            )
            return self._deny()
        except Exception:
            # Fail-closed: any unexpected error returns 403, never 500
            logger.exception(
                "TenantMiddleware: unexpected error resolving workspace %s for user %s",
                valid_uuid,
                user.pk,
            )
            return self._deny()

        request.tenant = membership.organization
        request.tenant_role = membership.role

        return self.get_response(request)

    @staticmethod
    def _deny() -> JsonResponse:
        """
        Return a uniform 403 response.
        Generic message prevents information leakage about why access was denied.
        """
        return JsonResponse(
            {"detail": "Access denied to the specified workspace."},
            status=403,
        )
