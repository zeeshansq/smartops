from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse


from dashboard.views import LandingPageView

# Configure Admin Site Metadata & Return-to-Site Link
admin.site.site_header = "SmartOps Platform Admin"
admin.site.site_title = "SmartOps Admin"
admin.site.index_title = "Platform Management Console"
admin.site.site_url = "/"  # 'Return to site' link points to root landing page


def root_health_check(request):
    """
    API Health Endpoint — provides system status and available API v1 routes.
    """
    return JsonResponse({
        "name": "SmartOps API",
        "status": "healthy",
        "version": "v1",
        "documentation": "/api/v1/",
        "endpoints": {
            "admin": "/admin/",
            "dashboard": "/dashboard/",
            "auth": "/api/v1/auth/",
            "workspaces": "/api/v1/workspaces/",
            "billing": "/api/v1/billing/",
            "ai": "/api/v1/ai/",
        }
    })


urlpatterns = [
    path('', LandingPageView.as_view(), name='platform-landing'),
    path('api/v1/health/', root_health_check, name='api-root-health'),
    path('admin/', admin.site.urls),
    path('dashboard/', include('dashboard.urls', namespace='dashboard')),
    path('api/v1/auth/', include('authentication.api.urls')),
    path('api/v1/workspaces/', include('organizations.api.urls')),
    path('api/v1/billing/', include('billing.api.urls')),
    path('api/v1/ai/', include('ai_services.api.urls')),
]
