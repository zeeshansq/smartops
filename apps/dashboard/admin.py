"""
Unfold admin customizations for the dashboard app.

The `dashboard_callback` function is registered in settings.UNFOLD as the
DASHBOARD_CALLBACK. Unfold calls it as:

    context = dashboard_callback(request, context)

and merges the returned dict into the admin index template context.
"""
import logging
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum, Count

logger = logging.getLogger(__name__)


def dashboard_callback(request, context):
    """
    Populate Unfold admin index with global KPI metrics.

    Called on every admin index page render. Queries are kept lightweight
    (aggregate-only, no full ORM object hydration).

    Returns the mutated `context` dict — Unfold merges it into the template.
    """
    try:
        from authentication.models import User
        from organizations.models import Organization
        from ai_services.models import AIRequestLog
        from billing.models import APIKey

        thirty_days_ago = timezone.now() - timedelta(days=30)

        # ── Aggregate KPI values ──────────────────────────────────────────
        total_users = User.objects.count()
        active_workspaces = Organization.objects.filter(is_active=True).count()
        total_ai_tokens = (
            AIRequestLog.objects.aggregate(t=Sum("tokens_used"))["t"] or 0
        )
        tokens_30d = (
            AIRequestLog.objects
            .filter(created_at__gte=thirty_days_ago)
            .aggregate(t=Sum("tokens_used"))["t"] or 0
        )
        active_api_keys = APIKey.objects.filter(is_active=True).count()
        ai_requests_30d = AIRequestLog.objects.filter(
            created_at__gte=thirty_days_ago
        ).count()

        # ── Unfold KPI card format ────────────────────────────────────────
        # Each card: {"title", "metric", "description", "icon", "change"}
        context["kpi_cards"] = [
            {
                "title": "Total Users",
                "metric": f"{total_users:,}",
                "description": "Registered accounts",
                "icon": "people",
                "change": None,
            },
            {
                "title": "Active Workspaces",
                "metric": f"{active_workspaces:,}",
                "description": "Active organizations",
                "icon": "corporate_fare",
                "change": None,
            },
            {
                "title": "AI Tokens (30d)",
                "metric": f"{tokens_30d:,}",
                "description": f"{total_ai_tokens:,} all-time",
                "icon": "bolt",
                "change": None,
            },
            {
                "title": "AI Requests (30d)",
                "metric": f"{ai_requests_30d:,}",
                "description": "Async LLM jobs",
                "icon": "smart_toy",
                "change": None,
            },
            {
                "title": "Active API Keys",
                "metric": f"{active_api_keys:,}",
                "description": "Across all workspaces",
                "icon": "key",
                "change": None,
            },
        ]

        # ── Recent AI logs for admin dashboard table ───────────────────────
        context["recent_ai_logs"] = (
            AIRequestLog.objects
            .select_related("organization")
            .order_by("-created_at")[:8]
        )

    except Exception:
        logger.exception("dashboard_callback: failed to compute KPI metrics")
        context.setdefault("kpi_cards", [])
        context.setdefault("recent_ai_logs", [])

    return context
