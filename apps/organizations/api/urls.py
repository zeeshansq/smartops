from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import OrganizationViewSet, OrganizationMemberViewSet

router = DefaultRouter()
router.register(r'', OrganizationViewSet, basename='organization')

# Member sub-resource URLs are defined manually so we can nest them
# under a specific workspace ID while keeping DRF router conventions.
urlpatterns = [
    # Workspace CRUD: GET/POST /api/v1/workspaces/
    #                 GET/PATCH/DELETE /api/v1/workspaces/{id}/
    path('', include(router.urls)),

    # Member management nested under a specific workspace
    # GET    /api/v1/workspaces/{org_id}/members/
    # POST   /api/v1/workspaces/{org_id}/members/
    # DELETE /api/v1/workspaces/{org_id}/members/{pk}/
    path(
        '<uuid:org_id>/members/',
        OrganizationMemberViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='workspace-members-list',
    ),
    path(
        '<uuid:org_id>/members/<uuid:pk>/',
        OrganizationMemberViewSet.as_view({'delete': 'destroy'}),
        name='workspace-members-detail',
    ),
]
