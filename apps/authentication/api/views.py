import logging
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from .serializers import UserSerializer, RegisterSerializer, ProfileUpdateSerializer

logger = logging.getLogger(__name__)


class RegisterView(generics.CreateAPIView):
    """
    POST /api/v1/auth/register/

    Creates a new user account. Open to anonymous requests (no auth required).

    Security:
    - Throttled with AnonRateThrottle (default: 20/min) to prevent brute-force
      account creation / email enumeration.
    - Password is validated against AUTH_PASSWORD_VALIDATORS before saving.
    - Response returns UserSerializer data (never the password).
    - Returns 201 on success; 400 with field-level errors on failure.
    """

    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        logger.info(
            "New user registered: %s (id=%s)",
            user.email,
            user.pk,
        )

        # Return the read-only UserSerializer representation, not the write serializer
        return Response(
            UserSerializer(user).data,
            status=status.HTTP_201_CREATED,
        )


class ProfileView(generics.RetrieveUpdateAPIView):
    """
    GET  /api/v1/auth/me/  — Retrieve the current user's profile.
    PATCH /api/v1/auth/me/  — Partially update first_name / last_name.

    Security:
    - Requires a valid JWT Bearer token (IsAuthenticated).
    - get_object() always returns request.user — no ID in the URL path,
      which completely prevents IDOR (Insecure Direct Object Reference).
    - Email changes are intentionally not allowed here; they require a
      dedicated verified-email-change flow.
    """

    permission_classes = [IsAuthenticated]

    def get_object(self):
        """Return the requesting user. No pk lookup = no IDOR risk."""
        return self.request.user

    def get_serializer_class(self):
        if self.request.method in ('PUT', 'PATCH'):
            return ProfileUpdateSerializer
        return UserSerializer
