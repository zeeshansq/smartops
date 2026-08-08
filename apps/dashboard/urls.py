"""
URL configuration for the client-facing dashboard.
"""
from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    # ── Auth ──────────────────────────────────────────────────────────────
    path(
        "login/",
        views.CustomLoginView.as_view(),
        name="login",
    ),
    path(
        "logout/",
        auth_views.LogoutView.as_view(next_page="/dashboard/login/"),
        name="logout",
    ),

    # ── Pages ─────────────────────────────────────────────────────────────
    path("", views.DashboardHomeView.as_view(), name="home"),
    path(
        "workspace/<uuid:org_id>/",
        views.WorkspaceDetailView.as_view(),
        name="workspace-detail",
    ),
    path(
        "demo-credentials/",
        views.DemoCredentialsDownloadView.as_view(),
        name="demo-credentials",
    ),
]
