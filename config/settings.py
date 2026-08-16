import os
import sys
import logging
from pathlib import Path
import environ

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# Add 'apps' folder to sys.path to allow clean imports
# e.g. `from authentication.models import User`
sys.path.insert(0, os.path.join(BASE_DIR, 'apps'))

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
env = environ.Env(
    DEBUG=(bool, False),                                # Safe default: never debug in prod
    IS_PRODUCTION=(bool, False),
    ALLOWED_HOSTS=(list, ['127.0.0.1', 'localhost']),
    CSRF_TRUSTED_ORIGINS=(list, []),
    INTERNAL_IPS=(list, ['127.0.0.1']),
    CONN_MAX_AGE=(int, 60),
    THROTTLE_RATE_ANON=(str, '20/min'),
    THROTTLE_RATE_USER=(str, '200/min'),
    REDIS_URL=(str, 'redis://127.0.0.1:6379/0'),
)

env_file = BASE_DIR / '.env'
if env_file.exists():
    environ.Env.read_env(str(env_file))

# ---------------------------------------------------------------------------
# Core Security — CRITICAL: No fallback for SECRET_KEY. Must be set in env.
# ---------------------------------------------------------------------------
SECRET_KEY = env('SECRET_KEY')   # Raises ImproperlyConfigured if absent

DEBUG = env('DEBUG')
IS_PRODUCTION = env('IS_PRODUCTION')

ALLOWED_HOSTS = env('ALLOWED_HOSTS')
CSRF_TRUSTED_ORIGINS = env('CSRF_TRUSTED_ORIGINS')
INTERNAL_IPS = env('INTERNAL_IPS')


def environment_callback(request):
    """Return (label, css_class) for the Unfold environment badge."""
    if IS_PRODUCTION:
        return "Production", "danger"
    return "Development", "warning"

# ---------------------------------------------------------------------------
# Application definition
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    'unfold',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',

    # Local apps
    'authentication.apps.AuthenticationConfig',
    'organizations.apps.OrganizationsConfig',
    'billing.apps.BillingConfig',
    'ai_services.apps.AiServicesConfig',
    'dashboard.apps.DashboardConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'organizations.middleware.TenantMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
DATABASES = {
    'default': {
        **env.db('DATABASE_URL', default=f'sqlite:///{BASE_DIR / "db.sqlite3"}'),
        'CONN_MAX_AGE': env('CONN_MAX_AGE'),      # Persistent connections (M3)
        'CONN_HEALTH_CHECKS': True,               # Validate connection before reuse
    }
}

# ---------------------------------------------------------------------------
# Custom User Model
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = 'authentication.User'

# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': env('THROTTLE_RATE_ANON'),
        'user': env('THROTTLE_RATE_USER'),
    },
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'EXCEPTION_HANDLER': 'rest_framework.views.exception_handler',
}

# ---------------------------------------------------------------------------
# Simple JWT
# ---------------------------------------------------------------------------
from datetime import timedelta  # noqa: E402 — placed here to keep settings grouped

SIMPLE_JWT = {
    # Token lifetimes
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),

    # Security
    'ROTATE_REFRESH_TOKENS': True,        # Issue new refresh token on every refresh
    'BLACKLIST_AFTER_ROTATION': True,     # Invalidate old refresh tokens immediately
    'UPDATE_LAST_LOGIN': True,            # Keep last_login field current

    # Algorithm
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,

    # Claims
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',

    # Token classes
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
}

# ---------------------------------------------------------------------------
# Password Validation  (C3 — minimum 12 characters for B2B SaaS standard)
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 12,
        },
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static Files
# ---------------------------------------------------------------------------
STATIC_URL = 'static/'

# Guard against missing static directory to prevent startup errors (L3)
_static_dir = BASE_DIR / 'static'
STATICFILES_DIRS = [_static_dir] if _static_dir.exists() else []
STATIC_ROOT = BASE_DIR / 'staticfiles'

# ---------------------------------------------------------------------------
# Default primary key type
# ---------------------------------------------------------------------------
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---------------------------------------------------------------------------
# Session-auth Login (used by client-facing dashboard templates)
# ---------------------------------------------------------------------------
LOGIN_URL = '/dashboard/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/dashboard/login/'

# ---------------------------------------------------------------------------
# django-unfold — Modernized Admin Configuration
# ---------------------------------------------------------------------------
UNFOLD = {
    "SITE_TITLE": "SmartOps Admin",
    "SITE_HEADER": "SmartOps",
    "SITE_URL": "/dashboard/",
    "SITE_SYMBOL": "electric_bolt",
    # Dashboard KPI callback — called on every admin index render
    "DASHBOARD_CALLBACK": "dashboard.admin.dashboard_callback",
    # Environment badge (shown in sidebar header)
    "ENVIRONMENT": "config.settings.environment_callback",
    # Brand colours — indigo/purple palette
    "COLORS": {
        "primary": {
            "50":  "238 242 255",
            "100": "224 231 255",
            "200": "199 210 254",
            "300": "165 180 252",
            "400": "129 140 248",
            "500": "99  102 241",
            "600": "79   70 229",
            "700": "67   56 202",
            "800": "55   48 163",
            "900": "49   46 129",
            "950": "30   27  75",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": True,
        "navigation": [
            {
                "title": "Platform",
                "separator": True,
                "items": [
                    {
                        "title": "Users",
                        "icon": "people",
                        "link": "/admin/authentication/user/",
                        "permission": lambda request: request.user.is_staff,
                    },
                    {
                        "title": "Organizations",
                        "icon": "corporate_fare",
                        "link": "/admin/organizations/organization/",
                        "permission": lambda request: request.user.is_staff,
                    },
                    {
                        "title": "Memberships",
                        "icon": "group_add",
                        "link": "/admin/organizations/organizationmember/",
                        "permission": lambda request: request.user.is_staff,
                    },
                ],
            },
            {
                "title": "Billing & AI",
                "separator": True,
                "items": [
                    {
                        "title": "API Keys",
                        "icon": "key",
                        "link": "/admin/billing/apikey/",
                        "permission": lambda request: request.user.is_staff,
                    },
                    {
                        "title": "AI Request Logs",
                        "icon": "smart_toy",
                        "link": "/admin/ai_services/airequestlog/",
                        "permission": lambda request: request.user.is_staff,
                    },
                ],
            },
        ],
    },
    "LOGIN": {
        "image": None,
        "redirect_after": "/admin/",
    },
}

# ---------------------------------------------------------------------------
# Security Headers — always-on baseline (OWASP)
# ---------------------------------------------------------------------------
SECURE_BROWSER_XSS_FILTER = True          # Legacy IE XSS auditor
X_FRAME_OPTIONS = 'DENY'                  # Prevent clickjacking
SECURE_CONTENT_TYPE_NOSNIFF = True        # Prevent MIME sniffing
REFERRER_POLICY = 'strict-origin-when-cross-origin'

# ---------------------------------------------------------------------------
# Session & CSRF Cookie Hardening  (H2)
# ---------------------------------------------------------------------------
SESSION_COOKIE_HTTPONLY = True            # Never accessible via JS
SESSION_COOKIE_SAMESITE = 'Lax'          # CSRF protection for session cookie
CSRF_COOKIE_HTTPONLY = True              # CSRF token not readable by JS
CSRF_COOKIE_SAMESITE = 'Lax'            # SameSite on CSRF cookie

# ---------------------------------------------------------------------------
# Production-only HTTPS Hardening  (H1)
# Gated behind IS_PRODUCTION so local HTTP dev continues to work.
# ---------------------------------------------------------------------------
if IS_PRODUCTION:
    SECURE_SSL_REDIRECT = True            # Redirect all HTTP → HTTPS
    SECURE_HSTS_SECONDS = 31536000        # HSTS: 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True # Apply HSTS to all subdomains
    SECURE_HSTS_PRELOAD = True            # Allow HSTS preload list submission
    SESSION_COOKIE_SECURE = True          # Session cookie only over HTTPS
    CSRF_COOKIE_SECURE = True             # CSRF cookie only over HTTPS
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')  # Trust proxy SSL
else:
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False

# ---------------------------------------------------------------------------
# Logging  (L4)
# Structured logging — console in dev, ready for external aggregation in prod.
# ---------------------------------------------------------------------------
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name} {process:d} {thread:d} — {message}',
            'style': '{',
        },
        'simple': {
            'format': '[{asctime}] {levelname} {name} — {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'console_prod': {
            'level': 'WARNING',
            'filters': ['require_debug_false'],
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.security': {
            'handlers': ['console', 'console_prod'],
            'level': 'WARNING',
            'propagate': False,
        },
        'authentication': {
            'handlers': ['console', 'console_prod'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'organizations': {
            'handlers': ['console', 'console_prod'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'billing': {
            'handlers': ['console', 'console_prod'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'ai_services': {
            'handlers': ['console', 'console_prod'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'dashboard': {
            'handlers': ['console', 'console_prod'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
}

# ---------------------------------------------------------------------------
# Celery & Redis Configuration
# ---------------------------------------------------------------------------
REDIS_URL = env('REDIS_URL')

CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes hard time limit

# ---------------------------------------------------------------------------
# Authentication Redirects
# ---------------------------------------------------------------------------
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/dashboard/login/'

# ---------------------------------------------------------------------------
# Test Runner
# ---------------------------------------------------------------------------
TEST_RUNNER = 'config.runner.SmartOpsTestRunner'


