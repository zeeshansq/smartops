"""
SmartOps — Deterministic Database Seeder
=========================================
Generates rich, realistic multi-tenant dummy data for local development,
UI testing, and client demonstrations.

Coverage:
    - Users (staff + regular, multi-domain)
    - Organizations / Workspaces (industry-specific)
    - OrganizationMemberships (Owner / Admin / Member RBAC)
    - Billing API Keys (named, last-used metadata)
    - AI Request Logs (completed / failed / processing / pending
                       with full response JSON and token accounting)
    - TEST_CREDENTIALS.txt  written to project root after every run

Usage:
    python manage.py seed_data
    python manage.py seed_data --clean
    python manage.py seed_data --users 60 --orgs 15 --ai-logs 500
"""

import os
import random
import uuid
from datetime import datetime, timedelta
from typing import List

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify
from faker import Faker

from authentication.models import User
from organizations.models import Organization, OrganizationMember
from billing.models import APIKey
from ai_services.models import AIRequestLog


# ─────────────────────────────────────────────────────────────────────────────
# Static Pools — realistic industry-grade data
# ─────────────────────────────────────────────────────────────────────────────

ORGANISATION_NAMES = [
    # FinTech
    "Apex Capital Partners",
    "Vanguard FinOps Platform",
    "Meridian Wealth Management",
    # SaaS / Tech
    "NexusCloud Technologies",
    "ByteCraft Engineering Studios",
    "Horizon AI Ventures",
    "Velox Enterprise Software",
    "Pulse Data Engine",
    # Healthcare / Bio
    "OmniHealth Platform",
    "BioSync Research Labs",
    # Security / Infrastructure
    "CyberShield Systems",
    "Apex Global Security",
    "IronWall Network Solutions",
    # Logistics / Operations
    "Synergy Logistics Group",
    "AeroEdge Supply Chain",
    # Analytics / Media
    "Starlight Media Intelligence",
    "Quantum Analytics Inc",
    "GridSense Industrial IoT",
    # Government / Enterprise
    "CloudScale Federal Networks",
    "Zenith Strategic Consulting",
]

EMAIL_DOMAINS = [
    "techcorp.io",
    "smartops-client.com",
    "devlabs.org",
    "enterprise-co.net",
    "cloudnative.co",
    "finopsglobal.com",
    "nexustech.ai",
    "bytecloud.dev",
    "horizonventures.io",
    "securenet.biz",
]

API_KEY_NAMES = [
    "Production AI Service Pipeline",
    "Staging LLM Processing Key",
    "Customer Support Chatbot Key",
    "Data Analytics Automation Engine",
    "Internal ETL Workflow Key",
    "Backup Provider Failover Key",
    "CI/CD Integration Service Key",
    "Mobile App Backend Middleware",
    "Third-Party Webhook Receiver",
    "Report Generation Service Key",
    "Document Intelligence Pipeline",
    "Audit & Compliance Export Key",
]

LLM_MODELS = [
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4-turbo",
    "claude-3-5-sonnet-20241022",
    "claude-3-haiku-20240307",
    "gemini-1.5-pro-latest",
    "gemini-1.5-flash",
    "mistral-large-latest",
    "mistral-8x7b-instruct",
    "meta/llama-3-70b-instruct",
]

PROMPT_POOL = [
    # Analytics & Reports
    "Summarize the Q3 financial performance report and highlight all key risk indicators for the board presentation.",
    "Analyze the 90-day server telemetry logs and identify root-cause anomalies in CPU spike frequency patterns.",
    "Produce an executive summary of YTD sales funnel conversion rates with strategic recommendations.",
    # Legal & Compliance
    "Extract structured entities (vendor name, contract value, SLA terms, expiry date) from this MSA agreement text.",
    "Review security policy documentation for compliance gaps against ISO 27001 Annex A control objectives.",
    "Draft GDPR-compliant data processing addendum clauses for our enterprise B2B subscription agreement.",
    # Software Engineering
    "Generate a Python async handler for processing multi-tenant webhook payloads with idempotency guarantees.",
    "Review this database schema and generate SQL optimization suggestions for the N+1 query bottlenecks.",
    "Refactor this monolithic authentication module into a composable middleware service using dependency injection.",
    # Content & Communications
    "Draft a professional email response to an enterprise client requesting custom SLA escalation terms.",
    "Translate our product release specification into clear, non-technical release notes for end customers.",
    "Generate 10 LinkedIn post variants announcing our platform's SOC 2 Type II certification.",
    # Data Intelligence
    "Parse this raw JSON API response and extract all customer churn signals for CRM enrichment.",
    "Classify incoming support tickets by severity tier and suggested resolution team using this taxonomy schema.",
    "Generate a competitive analysis framework comparing our feature set against Salesforce, HubSpot, and Zoho.",
    # Operations
    "Create an incident post-mortem document for the March 15 database connectivity outage with RCA and action items.",
    "Summarize 200 customer feedback entries and cluster them into 5 actionable product improvement themes.",
]

ERROR_MESSAGES = [
    "Upstream LLM Provider API timeout after 30,000 ms — connection refused on port 443.",
    "Rate limit exceeded: HTTP 429 Too Many Requests — retry after 60 seconds.",
    "Context window overflow: input token count (128,412) exceeds model hard limit (128,000).",
    "Upstream service degradation: HTTP 503 Service Unavailable — provider status page indicates incident.",
    "API key authorization rejected by upstream provider: HTTP 401 Unauthorized.",
    "Invalid model identifier provided: model 'gpt-5-turbo' is not yet available in API.",
    "JSON schema validation failed: response body could not be parsed as valid JSON.",
    "Task worker lost connection to Redis broker — task could not be acknowledged.",
    "Response content moderation filter triggered: prompt flagged for policy violation.",
    "Network socket error: connection reset by peer during streaming response.",
]

INDUSTRY_OUTPUTS = {
    "financial": [
        "Q3 EBITDA declined 4.2% YoY, driven primarily by elevated infrastructure costs and delayed enterprise contract closures. Three key risk indicators flagged: FX exposure in EMEA segment (+12%), vendor concentration in cloud services (single-vendor dependency 67%), and receivables aging >90 days up 18%. Board recommendation: initiate vendor diversification audit by EOQ4.",
        "Revenue performance summary — ARR: $24.3M (+31% YoY), NRR: 118%, CAC Payback: 14 months. Churn rate stable at 1.8% MoM. Expansion revenue contributed 42% of new ARR, signaling strong product-market fit in enterprise segment. Pipeline coverage ratio: 3.2x target.",
    ],
    "engineering": [
        "Schema analysis complete. Identified 3 N+1 query patterns in `order_items` → `products` join path. Recommendation: add composite index on `(order_id, product_id, created_at)`. Estimated query time reduction: 89% (from avg 420ms → 46ms). Migration script generated with zero-downtime index creation strategy using CONCURRENTLY clause.",
        "Async webhook handler scaffolded with idempotency key validation using Redis SET NX with 24-hour TTL. Implements tenant isolation via header-based routing, HMAC-SHA256 signature verification, and dead-letter queue for failed deliveries. Estimated throughput: 12,000 events/minute per worker instance.",
    ],
    "compliance": [
        "ISO 27001 compliance gap analysis complete. 94 controls evaluated across Annex A. Status: 78 controls Compliant, 12 Partially Compliant, 4 Non-Compliant. Priority remediation items: A.9.4.2 (Privileged Access Management — no formal review process), A.12.6.1 (Vulnerability Management — scan frequency insufficient). Full remediation roadmap document attached.",
        "GDPR DPA clause review complete. Key additions required: Article 28(3)(e) — Sub-processor change notification period must be extended from 10 to 30 business days. Article 17 — Right to erasure response SLA must be explicitly defined (max 72 hours). Updated clause templates generated and ready for legal review.",
    ],
    "operations": [
        "Incident post-mortem complete. RCA: database connection pool exhaustion triggered by unindexed full-table scan on `ai_request_logs` (61M rows) during scheduled reporting job. Timeline: 14:32 UTC alert raised → 14:48 UTC root cause identified → 15:12 UTC fix deployed. Total MTTR: 40 minutes. Prevention: index added, query optimized, scheduled job moved to read replica.",
        "Customer feedback clustering complete (247 entries analyzed). Theme distribution: Feature Requests 34%, Performance Issues 28%, Onboarding Friction 21%, Documentation Gaps 12%, Billing Queries 5%. Top 3 actionable themes: (1) SSO/SAML integration demand (43 mentions), (2) API rate limit increases (38 mentions), (3) Bulk export functionality (29 mentions).",
    ],
}


# ─────────────────────────────────────────────────────────────────────────────
# Helper Utilities
# ─────────────────────────────────────────────────────────────────────────────

def _pick_output(model: str, prompt: str) -> str:
    """Return a realistic-looking LLM output string based on prompt context."""
    prompt_lower = prompt.lower()
    if any(k in prompt_lower for k in ["financial", "revenue", "q3", "arr", "ebitda", "sales"]):
        return random.choice(INDUSTRY_OUTPUTS["financial"])
    if any(k in prompt_lower for k in ["python", "sql", "database", "schema", "async", "webhook", "code"]):
        return random.choice(INDUSTRY_OUTPUTS["engineering"])
    if any(k in prompt_lower for k in ["gdpr", "iso", "compliance", "audit", "policy", "legal", "sla"]):
        return random.choice(INDUSTRY_OUTPUTS["compliance"])
    return random.choice(INDUSTRY_OUTPUTS["operations"])


def _random_past_datetime(min_days: int = 0, max_days: int = 90) -> any:
    """Return a timezone-aware datetime in the recent past."""
    return timezone.now() - timedelta(
        days=random.randint(min_days, max_days),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
        seconds=random.randint(0, 59),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Management Command
# ─────────────────────────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = "Seeds the database with rich, realistic multi-tenant dummy data for SmartOps."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clean",
            action="store_true",
            help="Wipe all non-superuser data before generating new seed data.",
        )
        parser.add_argument(
            "--users",
            type=int,
            default=40,
            help="Number of regular users to generate (default: 40).",
        )
        parser.add_argument(
            "--orgs",
            type=int,
            default=12,
            help="Number of organizations (workspaces) to generate (default: 12).",
        )
        parser.add_argument(
            "--ai-logs",
            type=int,
            default=500,
            help="Total number of AI request logs to generate across orgs (default: 500).",
        )

    def handle(self, *args, **options):  # noqa: C901
        fake = Faker()
        fake.seed_instance(42)   # Reproducible deterministic seeding
        random.seed(42)

        clean = options["clean"]
        num_users = options["users"]
        num_orgs = min(options["orgs"], len(ORGANISATION_NAMES))
        num_ai_logs = options["ai_logs"]

        # ─── Banner ──────────────────────────────────────────────────────────
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("=" * 65))
        self.stdout.write(self.style.MIGRATE_HEADING("   SmartOps -- Enterprise Multi-Tenant Data Generator"))
        self.stdout.write(self.style.MIGRATE_HEADING("=" * 65))
        self.stdout.write(f"  Users Target      : {num_users}")
        self.stdout.write(f"  Organisations     : {num_orgs}")
        self.stdout.write(f"  AI Request Logs   : {num_ai_logs}")
        self.stdout.write(self.style.MIGRATE_HEADING("=" * 65))
        self.stdout.write("")

        with transaction.atomic():

            # ── Step 0: Optionally wipe existing data ─────────────────────
            if clean:
                self.stdout.write(self.style.WARNING("[!] --clean flag detected. Purging existing test data..."))
                AIRequestLog.objects.all().delete()
                APIKey.objects.all().delete()
                OrganizationMember.objects.all().delete()
                Organization.objects.all().delete()
                User.objects.filter(is_superuser=False).delete()
                self.stdout.write(self.style.SUCCESS("[OK] All test data purged.\n"))

            # ── Step 1: Ensure Platform Superuser ─────────────────────────
            self.stdout.write(self.style.MIGRATE_LABEL("[1/6] Platform Administrator Account"))
            admin_email = "admin@smartops.com"
            admin_user, created = User.objects.get_or_create(
                email=admin_email,
                defaults={
                    "first_name": "Platform",
                    "last_name": "Administrator",
                    "is_staff": True,
                    "is_superuser": True,
                    "is_active": True,
                    "is_email_verified": True,
                    "last_login_ip": "127.0.0.1",
                    "date_joined": timezone.now() - timedelta(days=365),
                },
            )
            if created:
                admin_user.set_password("AdminPass123!")
                admin_user.save()
                self.stdout.write(self.style.SUCCESS(f"  [OK] Created -> {admin_email}  (Pass: AdminPass123!)"))
            else:
                self.stdout.write(f"  [--] Already exists -> {admin_email}")

            # ── Step 2: Generate a diverse set of staff members ──────────
            self.stdout.write(self.style.MIGRATE_LABEL("\n[2/6] Staff & Internal Users"))
            staff_specs = [
                ("Alice", "Chen",     "alice.chen@smartops.com",     True,  False),
                ("Marcus", "Rivera",  "marcus.rivera@smartops.com",  True,  False),
                ("Priya", "Sharma",   "priya.sharma@smartops.com",   True,  False),
                ("Omar", "Al-Hassan", "omar.hassan@smartops.com",    True,  False),
            ]
            staff_users: List[User] = [admin_user]
            for fname, lname, email, is_staff, is_super in staff_specs:
                u, c = User.objects.get_or_create(
                    email=email,
                    defaults={
                        "first_name": fname,
                        "last_name": lname,
                        "is_staff": is_staff,
                        "is_superuser": is_super,
                        "is_active": True,
                        "is_email_verified": True,
                        "last_login_ip": fake.ipv4_public(),
                        "date_joined": _random_past_datetime(30, 300),
                    },
                )
                if c:
                    u.set_password("AdminPass123!")
                    u.save()
                staff_users.append(u)
                verb = "Created" if c else "Exists "
                self.stdout.write(f"  [{verb}] {fname} {lname} <{email}>")

            # ── Step 3: Generate Regular Tenant Users ────────────────────
            self.stdout.write(self.style.MIGRATE_LABEL(f"\n[3/6] Regular Tenant Users  ({num_users} target)"))
            regular_users: List[User] = []
            # Track plain-text credentials for the report file
            regular_user_creds: List[dict] = []
            attempts = 0
            while len(regular_users) < num_users and attempts < num_users * 3:
                attempts += 1
                fname = fake.first_name()
                lname = fake.last_name()
                domain = random.choice(EMAIL_DOMAINS)
                suffix = random.randint(1, 9999)
                email = f"{fname.lower()}.{lname.lower()}{suffix}@{domain}"

                if User.objects.filter(email=email).exists():
                    continue

                join_date = _random_past_datetime(1, 270)
                user = User.objects.create_user(
                    email=email,
                    password="Password123!",
                    first_name=fname,
                    last_name=lname,
                    is_active=random.choices([True, False], weights=[92, 8])[0],
                    is_email_verified=random.choices([True, False], weights=[88, 12])[0],
                    last_login_ip=fake.ipv4_public(),
                    date_joined=join_date,
                )
                regular_users.append(user)
                regular_user_creds.append({
                    "name": f"{fname} {lname}",
                    "email": email,
                    "password": "Password123!",
                    "active": user.is_active,
                })

            all_users: List[User] = staff_users + regular_users
            self.stdout.write(self.style.SUCCESS(f"  [OK] {len(regular_users)} regular users created. Total pool: {len(all_users)}"))

            # ── Step 4: Generate Organisations (Multi-Tenant Workspaces) ─
            self.stdout.write(self.style.MIGRATE_LABEL(f"\n[4/6] Organisations / Workspaces  ({num_orgs} target)"))
            org_sample = random.sample(ORGANISATION_NAMES, num_orgs)
            created_orgs: List[Organization] = []

            for i, name in enumerate(org_sample):
                base_slug = slugify(name)
                slug = base_slug
                if Organization.objects.filter(slug=slug).exists():
                    slug = f"{base_slug}-{i + 1}"

                # Vary: most orgs are active, 2 might be inactive for UI testing
                is_active = True if i < num_orgs - 2 else False

                org, org_created = Organization.objects.get_or_create(
                    slug=slug,
                    defaults={
                        "name": name,
                        "is_active": is_active,
                    },
                )
                created_orgs.append(org)
                status_label = "Created " if org_created else "Exists  "
                active_label = "ACTIVE" if org.is_active else "INACTIVE"
                self.stdout.write(f"  [{status_label}] {name} [{active_label}]")

            self.stdout.write(self.style.SUCCESS(f"  [OK] {len(created_orgs)} organisations ready."))

            # ── Step 5: Generate Memberships with Realistic RBAC ─────────
            self.stdout.write(self.style.MIGRATE_LABEL("\n[5/6] Organisation Memberships (RBAC)"))
            membership_count = 0
            membership_breakdown = {"owner": 0, "admin": 0, "member": 0}

            for idx, org in enumerate(created_orgs):
                # Each org gets 5–14 members
                k = min(len(all_users), random.randint(5, 14))
                org_users = random.sample(all_users, k=k)

                # Admin is guaranteed owner on first 4 orgs for easy demo navigation
                if idx < 4 and admin_user not in org_users:
                    org_users[0] = admin_user

                for member_idx, u in enumerate(org_users):
                    if member_idx == 0:
                        role = OrganizationMember.ROLE_OWNER
                        membership_breakdown["owner"] += 1
                    elif member_idx <= 2:
                        role = OrganizationMember.ROLE_ADMIN
                        membership_breakdown["admin"] += 1
                    else:
                        role = OrganizationMember.ROLE_MEMBER
                        membership_breakdown["member"] += 1

                    m, m_created = OrganizationMember.objects.get_or_create(
                        organization=org,
                        user=u,
                        defaults={
                            "role": role,
                            "is_active": random.choices([True, False], weights=[95, 5])[0],
                        },
                    )
                    if m_created:
                        membership_count += 1

            self.stdout.write(
                self.style.SUCCESS(
                    f"  [OK] {membership_count} memberships created "
                    f"(Owners: {membership_breakdown['owner']}, "
                    f"Admins: {membership_breakdown['admin']}, "
                    f"Members: {membership_breakdown['member']})"
                )
            )

            # ── Step 6a: Generate Billing API Keys ────────────────────────
            self.stdout.write(self.style.MIGRATE_LABEL("\n[6/6] Billing API Keys & AI Request Logs"))
            self.stdout.write("  [*] Generating API Keys...")
            total_keys = 0
            for org in created_orgs:
                num_keys = random.randint(3, 6)
                for _ in range(num_keys):
                    key_name = random.choice(API_KEY_NAMES)
                    suffix = random.randint(10, 99)
                    instance, _raw_key = APIKey.objects.create_key(
                        organization=org,
                        name=f"{key_name} #{suffix}",
                    )
                    instance.is_active = random.choices([True, False], weights=[87, 13])[0]
                    # Simulate varied last-used timestamps
                    if random.random() > 0.2:
                        instance.last_used_at = _random_past_datetime(0, 45)
                    instance.save()
                    total_keys += 1

            self.stdout.write(self.style.SUCCESS(f"  [OK] {total_keys} API Keys created across {len(created_orgs)} organisations."))

            # ── Step 6b: Generate AI Request Logs ────────────────────────
            self.stdout.write(f"  [*] Generating {num_ai_logs} AI Request Logs...")

            # Weighted status distribution — mirrors realistic production ratios
            status_pool = [
                (AIRequestLog.STATUS_COMPLETED,  74),
                (AIRequestLog.STATUS_FAILED,     16),
                (AIRequestLog.STATUS_PROCESSING,  7),
                (AIRequestLog.STATUS_PENDING,     3),
            ]
            status_choices, status_weights = zip(*status_pool)

            ai_logs_created = 0
            token_total = 0
            failed_count = 0
            completed_count = 0

            for _ in range(num_ai_logs):
                target_org = random.choice(created_orgs)
                org_memberships = list(target_org.members.all())
                if not org_memberships:
                    continue

                member_user = random.choice(org_memberships).user
                status = random.choices(status_choices, weights=status_weights)[0]
                model_name = random.choice(LLM_MODELS)
                prompt = random.choice(PROMPT_POOL)
                task_id = str(uuid.uuid4())
                created_time = _random_past_datetime(0, 90)

                log = AIRequestLog(
                    organization=target_org,
                    user=member_user,
                    task_id=task_id,
                    prompt=prompt,
                    status=status,
                    created_at=created_time,
                )

                if status == AIRequestLog.STATUS_COMPLETED:
                    prompt_tokens = random.randint(180, 1500)
                    completion_tokens = random.randint(250, 3500)
                    total_tokens = prompt_tokens + completion_tokens
                    log.tokens_used = total_tokens
                    log.response = {
                        "id": f"chatcmpl-{uuid.uuid4().hex[:24]}",
                        "model": model_name,
                        "status": "success",
                        "output": _pick_output(model_name, prompt),
                        "finish_reason": "stop",
                        "usage": {
                            "prompt_tokens": prompt_tokens,
                            "completion_tokens": completion_tokens,
                            "total_tokens": total_tokens,
                        },
                        "latency_ms": random.randint(480, 8200),
                        "cost_usd": round(total_tokens * 0.000015, 6),
                    }
                    token_total += total_tokens
                    completed_count += 1

                elif status == AIRequestLog.STATUS_FAILED:
                    wasted_tokens = random.randint(20, 200)
                    log.tokens_used = wasted_tokens
                    error_msg = random.choice(ERROR_MESSAGES)
                    log.error_message = error_msg
                    log.response = {
                        "status": "error",
                        "error_code": random.choice([
                            "UPSTREAM_TIMEOUT", "RATE_LIMIT_EXCEEDED",
                            "CONTEXT_OVERFLOW", "PROVIDER_UNAVAILABLE",
                            "AUTH_REJECTED", "CONTENT_FILTERED",
                        ]),
                        "error_message": error_msg,
                        "retry_after": random.choice([None, 30, 60, 120]),
                        "usage": {
                            "prompt_tokens": wasted_tokens,
                            "completion_tokens": 0,
                            "total_tokens": wasted_tokens,
                        },
                    }
                    token_total += wasted_tokens
                    failed_count += 1

                elif status == AIRequestLog.STATUS_PROCESSING:
                    log.tokens_used = 0
                    log.response = {
                        "status": "processing",
                        "message": "Task is being executed by async worker.",
                        "queue_position": random.randint(1, 8),
                        "estimated_completion_ms": random.randint(2000, 15000),
                    }

                else:  # PENDING
                    log.tokens_used = 0
                    log.response = {
                        "status": "pending",
                        "message": "Task queued. Awaiting available Celery worker.",
                    }

                log.save()
                # Override auto_now_add so logs are distributed across 90 days
                AIRequestLog.objects.filter(id=log.id).update(created_at=created_time)
                ai_logs_created += 1

            self.stdout.write(
                self.style.SUCCESS(
                    f"  [OK] {ai_logs_created} AI Request Logs created "
                    f"(Completed: {completed_count}, Failed: {failed_count}, "
                    f"Tokens Processed: {token_total:,})"
                )
            )

        # ── Final Summary (console) ───────────────────────────────────────
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("=" * 65))
        self.stdout.write(self.style.SUCCESS("   Seed Data Generation Complete!"))
        self.stdout.write(self.style.MIGRATE_HEADING("=" * 65))
        self.stdout.write("")
        self.stdout.write(self.style.NOTICE("  TEST CREDENTIALS"))
        self.stdout.write(self.style.NOTICE("  " + "-" * 55))
        self.stdout.write(self.style.NOTICE("  Platform Admin  :  admin@smartops.com  / AdminPass123!"))
        self.stdout.write(self.style.NOTICE("  Staff Users     :  alice.chen@smartops.com  / AdminPass123!"))
        self.stdout.write(self.style.NOTICE("                  :  marcus.rivera@smartops.com  / AdminPass123!"))
        self.stdout.write(self.style.NOTICE("                  :  priya.sharma@smartops.com  / AdminPass123!"))
        self.stdout.write(self.style.NOTICE("  Regular Users   :  (any generated email)  / Password123!"))
        self.stdout.write(self.style.NOTICE("  " + "-" * 55))
        self.stdout.write(self.style.NOTICE("  Web Dashboard   :  http://127.0.0.1:8000/dashboard/"))
        self.stdout.write(self.style.NOTICE("  Admin Console   :  http://127.0.0.1:8000/admin/"))
        self.stdout.write(self.style.NOTICE("  API Base URL    :  http://127.0.0.1:8000/api/v1/"))
        self.stdout.write(self.style.NOTICE("  " + "-" * 55))
        self.stdout.write("")

        # ── Write TEST_CREDENTIALS.txt to project root ────────────────────
        self._write_credentials_file(
            regular_user_creds=regular_user_creds,
            created_orgs=created_orgs,
            total_keys=total_keys,
            ai_logs_created=ai_logs_created,
            token_total=token_total,
        )

    # ─────────────────────────────────────────────────────────────────────
    def _write_credentials_file(
        self,
        regular_user_creds: list,
        created_orgs: list,
        total_keys: int,
        ai_logs_created: int,
        token_total: int,
    ):
        """
        Write a human-readable TEST_CREDENTIALS.txt to the Django project root
        (the directory containing manage.py).
        """
        # Resolve project root: walk up 5 directory levels from this file
        # seed_data.py -> commands -> management -> dashboard -> apps -> smartops
        project_root = os.path.dirname(
            os.path.dirname(
                os.path.dirname(
                    os.path.dirname(
                        os.path.dirname(os.path.abspath(__file__))
                    )
                )
            )
        )
        output_path = os.path.join(project_root, "TEST_CREDENTIALS.txt")
        generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        sep  = "=" * 72
        dash = "-" * 72
        thin = "-" * 40

        lines = [
            sep,
            "  SmartOps Platform  --  Test Credentials & Exploration Guide",
            f"  Generated : {generated_at}",
            sep,
            "",
            "  WHAT IS SmartOps?",
            thin,
            "  SmartOps is a production-grade, multi-tenant B2B SaaS boilerplate.",
            "  It demonstrates enterprise patterns such as isolated workspaces,",
            "  async AI task processing, role-based access control, and",
            "  cryptographically hashed API keys.",
            "",
            "  Use the credentials below to log in and explore every feature.",
            "",
            sep,
            "  QUICK ACCESS URLs",
            dash,
            "  Landing Page     :  http://127.0.0.1:8000/",
            "  Client Dashboard :  http://127.0.0.1:8000/dashboard/",
            "  Admin Console    :  http://127.0.0.1:8000/admin/",
            "  REST API Root    :  http://127.0.0.1:8000/api/v1/",
            "  JWT Login API    :  POST http://127.0.0.1:8000/api/v1/auth/token/",
            "",
            sep,
            "  PLATFORM ADMINISTRATOR  (Full System Access + Django Unfold Admin)",
            dash,
            "  Email    :  admin@smartops.com",
            "  Password :  AdminPass123!",
            "  Access   :  /admin/  and  /dashboard/  and all REST API endpoints",
            "",
            sep,
            "  STAFF USERS  (Admin Console Access)",
            dash,
            "  These users have is_staff=True and can log into /admin/.",
            "",
            "  Name              Email                              Password",
            "  " + thin,
            "  Alice Chen        alice.chen@smartops.com            AdminPass123!",
            "  Marcus Rivera     marcus.rivera@smartops.com         AdminPass123!",
            "  Priya Sharma      priya.sharma@smartops.com          AdminPass123!",
            "  Omar Al-Hassan    omar.hassan@smartops.com           AdminPass123!",
            "",
            sep,
            "  REGULAR TENANT USERS  (Client Dashboard Access)",
            dash,
            "  All regular users share the same password: Password123!",
            "  They can log in at /dashboard/login/ and access their workspaces.",
            "",
            f"  {'#':<4}  {'Full Name':<25}  {'Email':<45}  {'Status'}",
            "  " + dash,
        ]

        for idx, cred in enumerate(regular_user_creds, start=1):
            status = "ACTIVE  " if cred["active"] else "INACTIVE"
            lines.append(
                f"  {idx:<4}  {cred['name']:<25}  {cred['email']:<45}  {status}"
            )

        lines += [
            "",
            "  (All regular users)  Password :  Password123!",
            "",
            sep,
            "  ORGANISATIONS / WORKSPACES  (Isolated Tenants)",
            dash,
            "  Each workspace is a fully isolated tenant. Members can only see",
            "  data belonging to their own workspace.",
            "",
            f"  {'#':<4}  {'Workspace Name':<35}  {'Status'}",
            "  " + thin,
        ]

        for idx, org in enumerate(created_orgs, start=1):
            status = "ACTIVE  " if org.is_active else "INACTIVE"
            lines.append(f"  {idx:<4}  {org.name:<35}  {status}")

        lines += [
            "",
            sep,
            "  SEEDED DATA SUMMARY",
            dash,
            f"  Regular Tenant Users  :  {len(regular_user_creds)}",
            f"  Staff Users           :  4  (+ 1 superuser)",
            f"  Organisations         :  {len(created_orgs)}",
            f"  API Keys              :  {total_keys}",
            f"  AI Request Logs       :  {ai_logs_created}",
            f"  Total Tokens Tracked  :  {token_total:,}",
            "",
            sep,
            "  API QUICK-START  (use cURL or Postman)",
            dash,
            "  STEP 1 — Obtain JWT tokens:",
            "",
            "    POST /api/v1/auth/token/",
            "    Content-Type: application/json",
            "",
            '    { "email": "admin@smartops.com", "password": "AdminPass123!" }',
            "",
            "  STEP 2 — Create a Workspace:",
            "",
            "    POST /api/v1/workspaces/",
            "    Authorization: Bearer <access_token>",
            "",
            '    { "name": "My Company" }',
            "",
            "  STEP 3 — Generate an API Key:",
            "",
            "    POST /api/v1/billing/api-keys/",
            "    Authorization: Bearer <access_token>",
            "    X-Workspace-ID: <workspace_id>",
            "",
            '    { "name": "Production AI Key" }',
            "",
            "  STEP 4 — Trigger an async AI Task:",
            "",
            "    POST /api/v1/ai/generate/",
            "    Authorization: Bearer <access_token>",
            "    X-Workspace-ID: <workspace_id>",
            "",
            '    { "prompt": "Summarize Q3 report.", "model": "gpt-4o" }',
            "",
            "  Returns: { \"task_id\": \"...\", \"status\": \"pending\" }  (202 Accepted)",
            "",
            sep,
            "  NOTE: This file is auto-generated by:",
            "        python manage.py seed_data --clean",
            "  Do NOT commit this file to version control.",
            "  Ensure TEST_CREDENTIALS.txt is listed in .gitignore.",
            sep,
            "",
        ]

        content = "\n".join(lines)
        with open(output_path, "w", encoding="utf-8") as fh:
            fh.write(content)

        self.stdout.write(
            self.style.SUCCESS(f"  [OK] TEST_CREDENTIALS.txt written -> {output_path}")
        )
        self.stdout.write("")
