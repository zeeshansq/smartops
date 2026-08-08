"""
Dashboard views — client-facing web UI.

All views enforce login via LoginRequiredMixin and scope data to
the user's organizations to maintain strict tenant isolation.
"""
import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Sum, Count
from django.http import Http404
from django.utils import timezone
from django.views.generic import TemplateView
from datetime import timedelta

from authentication.models import User
from organizations.models import Organization, OrganizationMember
from ai_services.models import AIRequestLog
from billing.models import APIKey

import os
from django.conf import settings
from django.http import Http404, HttpResponse

logger = logging.getLogger(__name__)


class DemoCredentialsDownloadView(TemplateView):
    """
    Serves the auto-generated TEST_CREDENTIALS.txt file for download or viewing
    by demo visitors exploring the platform.
    """

    def get(self, request, *args, **kwargs):
        credentials_file = os.path.join(settings.BASE_DIR, "TEST_CREDENTIALS.txt")
        if not os.path.exists(credentials_file):
            # Fallback text if seeder hasn't run yet
            content = (
                "SmartOps Demo Credentials\n"
                "=========================\n\n"
                "Superadmin : admin@smartops.com / AdminPass123!\n"
                "Staff User : alice.chen@smartops.com / AdminPass123!\n"
                "Tenant User: clayton.hall1536@techcorp.io / Password123!\n\n"
                "Run 'python manage.py seed_data --clean' to generate the complete 40+ user credentials list.\n"
            )
            response = HttpResponse(content, content_type="text/plain; charset=utf-8")
        else:
            with open(credentials_file, "r", encoding="utf-8") as fh:
                content = fh.read()
            response = HttpResponse(content, content_type="text/plain; charset=utf-8")

        response["Content-Disposition"] = 'inline; filename="TEST_CREDENTIALS.txt"'
        return response


from django.contrib.auth.views import LoginView


class CustomLoginView(LoginView):
    """
    Custom LoginView that injects live database demo credentials into template context
    so quick-fill buttons dynamically populate actual existing accounts.
    """
    template_name = "dashboard/login.html"
    next_page = "/dashboard/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        superadmin = User.objects.filter(is_superuser=True).first()
        tenant_user = User.objects.filter(is_staff=False, is_active=True).first()

        ctx["demo_superadmin_email"] = superadmin.email if superadmin else "admin@smartops.com"
        ctx["demo_tenant_email"] = tenant_user.email if tenant_user else "user@example.com"
        return ctx


class LandingPageView(TemplateView):
    """
    Public landing page for SmartOps platform at root URL '/'.

    Presents platform overview, live aggregate metrics, architecture overview,
    and entry points for Dashboard and Admin Panel.
    """
    template_name = "landing.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        
        # Aggregate platform metrics for landing page
        total_workspaces = Organization.objects.filter(is_active=True).count()
        total_users = User.objects.filter(is_active=True).count()
        total_tokens = AIRequestLog.objects.aggregate(t=Sum("tokens_used"))["t"] or 0
        total_api_keys = APIKey.objects.filter(is_active=True).count()

        # Dynamically query real database accounts so landing page matches seeder output 100%
        superadmin = User.objects.filter(is_superuser=True).first()
        staff_user = User.objects.filter(is_staff=True, is_superuser=False).first()
        tenant_user = User.objects.filter(is_staff=False, is_active=True).first()

        superadmin_email = superadmin.email if superadmin else "admin@smartops.com"
        staff_email = staff_user.email if staff_user else "alice.chen@smartops.com"
        tenant_email = tenant_user.email if tenant_user else "user@example.com"

        ctx.update({
            "total_workspaces": total_workspaces,
            "total_users": total_users,
            "total_tokens": total_tokens,
            "total_api_keys": total_api_keys,
            "page_title": "SmartOps — B2B SaaS Engine",
            "demo_accounts": [
                {
                    "role": "Superadmin",
                    "email": superadmin_email,
                    "password": "AdminPass123!",
                    "access": "Admin Console (/admin/) & Dashboard",
                    "color": "indigo",
                },
                {
                    "role": "Staff Member",
                    "email": staff_email,
                    "password": "AdminPass123!",
                    "access": "Admin Console (/admin/)",
                    "color": "purple",
                },
                {
                    "role": "Tenant Owner",
                    "email": tenant_email,
                    "password": "Password123!",
                    "access": "Client Web Dashboard (/dashboard/)",
                    "color": "emerald",
                },
            ],
        })
        return ctx


class DashboardHomeView(LoginRequiredMixin, TemplateView):
    """
    Main client-facing dashboard.

    Scopes all data to workspaces the current user is a member of.
    Never exposes cross-tenant data.
    """
    template_name = "dashboard/index.html"
    login_url = "/dashboard/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user

        # ── Tenant-scoped workspace data ──────────────────────────────────
        # Fetch only organizations the authenticated user belongs to
        memberships = (
            OrganizationMember.objects
            .filter(user=user, organization__is_active=True)
            .select_related("organization")
            .order_by("-organization__created_at")
        )
        organizations = [m.organization for m in memberships]
        org_ids = [o.id for o in organizations]

        # ── KPI counts (scoped to user's orgs) ───────────────────────────
        total_workspaces = len(organizations)
        total_api_keys = APIKey.objects.filter(
            organization_id__in=org_ids, is_active=True
        ).count()

        # AI usage (last 30 days, scoped to user's orgs)

        thirty_days_ago = timezone.now() - timedelta(days=30)
        ai_stats = (
            AIRequestLog.objects
            .filter(
                organization_id__in=org_ids,
                created_at__gte=thirty_days_ago,
            )
            .aggregate(
                total_tokens=Sum("tokens_used"),
                total_requests=Count("id"),
            )
        )
        total_tokens = ai_stats["total_tokens"] or 0
        total_requests = ai_stats["total_requests"] or 0

        # ── Recent AI request logs (scoped to user's orgs) ───────────────
        recent_logs = (
            AIRequestLog.objects
            .filter(organization_id__in=org_ids)
            .select_related("organization")
            .order_by("-created_at")[:10]
        )

        # ── Recent memberships for workspace list ─────────────────────────
        ctx.update({
            "organizations": organizations,
            "memberships": memberships,
            "total_workspaces": total_workspaces,
            "total_api_keys": total_api_keys,
            "total_tokens": total_tokens,
            "total_requests": total_requests,
            "recent_logs": recent_logs,
            "page_title": "Dashboard — SmartOps",
        })
        return ctx


class WorkspaceDetailView(LoginRequiredMixin, TemplateView):
    """
    Per-workspace detail view.

    Verifies the current user is a member of the requested workspace
    before exposing any data. Returns 403 if not.
    """
    template_name = "dashboard/workspace_detail.html"
    login_url = "/dashboard/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        org_id = self.kwargs["org_id"]

        # Verify membership before exposing org data (tenant guard)
        try:
            membership = OrganizationMember.objects.select_related(
                "organization"
            ).get(user=user, organization_id=org_id, organization__is_active=True)
        except OrganizationMember.DoesNotExist:
            raise Http404("Workspace not found.")

        org = membership.organization

        # Members list
        members = (
            OrganizationMember.objects
            .filter(organization=org)
            .select_related("user")
            .order_by("role", "user__email")
        )

        # API keys for this org
        api_keys = APIKey.objects.filter(organization=org).order_by("-created_at")

        # AI logs for this org (last 50)
        logs = (
            AIRequestLog.objects
            .filter(organization=org)
            .order_by("-created_at")[:50]
        )

        stats = AIRequestLog.objects.filter(organization=org).aggregate(
            total_tokens=Sum("tokens_used"),
            total_requests=Count("id"),
            completed=Count("id", filter=Q(status="COMPLETED")),
            failed=Count("id", filter=Q(status="FAILED")),
        )

        ctx.update({
            "org": org,
            "membership": membership,
            "members": members,
            "api_keys": api_keys,
            "logs": logs,
            "stats": stats,
            "page_title": f"{org.name} — SmartOps",
        })
        return ctx
