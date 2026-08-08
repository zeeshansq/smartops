import logging
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from rest_framework import viewsets, status, mixins
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from organizations.models import Organization, OrganizationMember
from .permissions import IsWorkspaceAdminOrOwner
from .serializers import (
    OrganizationSerializer,
    OrganizationMemberSerializer,
    AddMemberSerializer,
)

User = get_user_model()
logger = logging.getLogger(__name__)


def _unique_slug(name: str) -> str:
    """
    Generate a unique slug from the organization name.
    Appends an incrementing suffix if the derived slug is already taken.
    """
    base_slug = slugify(name)
    slug = base_slug
    counter = 1
    while Organization.objects.filter(slug=slug).exists():
        slug = f'{base_slug}-{counter}'
        counter += 1
    return slug


class OrganizationViewSet(viewsets.ModelViewSet):
    """
    Workspace (Organization) CRUD.

    GET    /api/v1/workspaces/          — List workspaces the current user belongs to.
    POST   /api/v1/workspaces/          — Create a new workspace (user becomes owner).
    GET    /api/v1/workspaces/{id}/     — Retrieve a single workspace.
    PATCH  /api/v1/workspaces/{id}/     — Update workspace name (owner/admin only).
    DELETE /api/v1/workspaces/{id}/     — Soft-deactivate workspace (owner only).

    Tenant isolation:
    - `get_queryset()` is scoped to organizations where request.user has an
      ACTIVE membership. Users can never see other tenants' data.
    """

    serializer_class = OrganizationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Return only organizations where the requesting user is an active member.
        This is the primary tenant-isolation boundary for the workspace list.
        """
        return Organization.objects.filter(
            members__user=self.request.user,
            members__is_active=True,
            is_active=True,
        ).distinct()

    def perform_create(self, serializer):
        """
        Create the Organization and atomically create an 'owner' membership
        for the requesting user. Both operations succeed or both fail.
        """
        slug = _unique_slug(serializer.validated_data['name'])
        organization = serializer.save(slug=slug)

        OrganizationMember.objects.create(
            organization=organization,
            user=self.request.user,
            role=OrganizationMember.ROLE_OWNER,
        )
        logger.info(
            "Organization '%s' (id=%s) created by user %s",
            organization.name,
            organization.pk,
            self.request.user.pk,
        )


class OrganizationMemberViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    Workspace member management. Requires X-Workspace-ID header (resolved by
    TenantMiddleware) to establish tenant context.

    GET    /api/v1/workspaces/{org_id}/members/           — List members (any member).
    POST   /api/v1/workspaces/{org_id}/members/           — Add member (admin/owner only).
    DELETE /api/v1/workspaces/{org_id}/members/{id}/      — Remove member (admin/owner only).

    Tenant isolation:
    - `get_queryset()` is strictly scoped to `request.tenant`.
    - Non-members will have received a 403 from TenantMiddleware before reaching here.
    """

    serializer_class = OrganizationMemberSerializer

    def get_permissions(self):
        """
        Listing members requires only authentication (any workspace member can view).
        Adding or removing members requires admin/owner role.
        """
        if self.action in ('create', 'destroy'):
            return [IsAuthenticated(), IsWorkspaceAdminOrOwner()]
        return [IsAuthenticated()]

    def get_queryset(self):
        """
        Scope members to the current tenant (set by TenantMiddleware).
        Returns an empty queryset if no tenant context (should not happen
        in practice since TenantMiddleware guards unauthenticated access).
        """
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return OrganizationMember.objects.none()
        return OrganizationMember.objects.filter(
            organization=tenant,
        ).select_related('user')

    def create(self, request, *args, **kwargs):
        """
        Add a new member to the current workspace by their email address.
        Validates: user exists, not already a member, role is valid.
        """
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response(
                {'detail': 'X-Workspace-ID header is required.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = AddMemberSerializer(
            data=request.data,
            context={'organization': tenant},
        )
        serializer.is_valid(raise_exception=True)

        target_user = serializer._resolved_user
        role = serializer.validated_data['role']

        membership = OrganizationMember.objects.create(
            organization=tenant,
            user=target_user,
            role=role,
        )
        logger.info(
            "User %s added to workspace '%s' as %s by %s",
            target_user.email,
            tenant.name,
            role,
            request.user.email,
        )
        return Response(
            OrganizationMemberSerializer(membership).data,
            status=status.HTTP_201_CREATED,
        )

    def destroy(self, request, *args, **kwargs):
        """
        Remove a member from the current workspace.
        Prevents an owner from removing themselves to avoid ownerless workspaces.
        """
        membership = self.get_object()

        if membership.role == OrganizationMember.ROLE_OWNER and membership.user == request.user:
            return Response(
                {'detail': 'Workspace owners cannot remove themselves.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        logger.info(
            "Member %s removed from workspace '%s' by %s",
            membership.user.email,
            membership.organization.name,
            request.user.email,
        )
        membership.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
