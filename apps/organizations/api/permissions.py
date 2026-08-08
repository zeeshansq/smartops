from rest_framework.permissions import BasePermission


class IsWorkspaceAdminOrOwner(BasePermission):
    """
    Grants access only when the requesting user holds the 'admin' or 'owner'
    role in the currently scoped workspace (resolved by TenantMiddleware).

    Requires both:
    - `request.tenant` to be set (i.e., a valid X-Workspace-ID header was sent).
    - `request.tenant_role` to be 'admin' or 'owner'.

    Returns 403 in all other cases. The message is intentionally generic to
    avoid disclosing workspace membership information to unauthorized callers.
    """

    message = 'You do not have permission to perform this action in the specified workspace.'

    PRIVILEGED_ROLES = frozenset({'admin', 'owner'})

    def has_permission(self, request, view) -> bool:
        if not getattr(request, 'tenant', None):
            return False
        return getattr(request, 'tenant_role', None) in self.PRIVILEGED_ROLES
