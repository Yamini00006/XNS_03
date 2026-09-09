"""
backend/config/settings.py

Django settings for the Customer Data Platform backend (Member 2).

Design notes (see docs/api/README.md for the full write-up):
  - Django's ORM manages ONLY its own built-in tables (auth_user, sessions,
    etc). It does NOT define models for upload_files / processing_jobs /
    customers / etc — those tables are owned by Member 3 and are already
    defined via SQLAlchemy in database/schema/models.py + schema.sql.
  - All access to Member-3-owned tables happens through
    database.schema.connection.get_session() (see backend/common/db.py).
  - No secrets or machine-specific paths are hard-coded here; everything
    comes from environment variables / .env (see .env.example at the
    project root).
"""

import os
import sys
from datetime import timedelta
from pathlib import Path

# ─── Paths ──────────────────────────────────────────────────────
# backend/config/settings.py -> backend/ -> project root
BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent

# Make `data_processing` and `database` (Member 3's packages, which live
# at the project root, one level above backend/) importable regardless
# of the current working directory the server is started from.
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ─── Load .env (project root) ────────────────────────────────────
try:
    from dotenv import load_dotenv

    _env_file = PROJECT_ROOT / ".env"
    if _env_file.exists():
        load_dotenv(_env_file, override=False)
except ImportError:
    pass  # python-dotenv not installed — rely on real environment variables


def _env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


def _env_list(name: str, default: str = "") -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


# ─── Core ─────────────────────────────────────────────────────────
SECRET_KEY = os.getenv("SECRET_KEY", "changeme-in-production")
DEBUG = _env_bool("DEBUG", False)
ALLOWED_HOSTS = _env_list("ALLOWED_HOSTS", "localhost,127.0.0.1")

# ─── Applications ───────────────────────────────────────────────
# Member-2 apps expose views/urls only — they do not define Django models
# (Member-3-owned tables are accessed via SQLAlchemy, see backend/common/db.py).
# They are still registered as installed apps for consistency with the
# locked folder structure and so Django's app registry / test discovery
# works normally.
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "apps.users.apps.UsersConfig",
    "apps.files.apps.FilesConfig",
    "apps.processing.apps.ProcessingConfig",
    "apps.data.apps.DataConfig",
    "apps.dashboard.apps.DashboardConfig",
    "apps.exports.apps.ExportsConfig",
    "apps.chatbot.apps.ChatbotConfig",
]
# NOTE: apps/auth/ (JWT login/refresh/logout views) is intentionally NOT
# added to INSTALLED_APPS. It has no models and its label would collide
# with django.contrib.auth's "auth" app label. Its urls are wired directly
# in config/urls.py.

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ─── Database (Django's OWN tables only: auth_user, sessions, etc.) ──
# Member-3-owned tables (upload_files, processing_jobs, customers, ...)
# are accessed separately through SQLAlchemy — see backend/common/db.py.
# We point Django at the SAME Postgres database so auth_user lives
# alongside Member 3's tables (upload_files.uploaded_by references
# auth_user.id by convention, though not by a DB-level FK constraint).
_DATABASE_URL = os.getenv("DATABASE_URL")

if _DATABASE_URL:
    import re

    _m = re.match(
        r"^postgresql(?:\+psycopg2)?://(?P<user>[^:]*):(?P<password>[^@]*)@"
        r"(?P<host>[^:/]+):?(?P<port>\d*)/(?P<name>.+)$",
        _DATABASE_URL,
    )
    if _m:
        _db_kwargs = _m.groupdict()
        DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": _db_kwargs["name"],
                "USER": _db_kwargs["user"],
                "PASSWORD": _db_kwargs["password"],
                "HOST": _db_kwargs["host"],
                "PORT": _db_kwargs["port"] or "5432",
            }
        }
    else:
        # Fall back to individual DB_* vars if DATABASE_URL doesn't parse
        _DATABASE_URL = None

if not _DATABASE_URL:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("DB_NAME", "customer_data_platform"),
            "USER": os.getenv("DB_USER", "postgres"),
            "PASSWORD": os.getenv("DB_PASSWORD", "postgres"),
            "HOST": os.getenv("DB_HOST", "localhost"),
            "PORT": os.getenv("DB_PORT", "5432"),
        }
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ─── Password validation ─────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ─── I18N ─────────────────────────────────────────────────────────
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ─── Static files ─────────────────────────────────────────────────
STATIC_URL = "static/"

# ─── File uploads ──────────────────────────────────────────────────
# Where uploaded customer-data files are stored on disk before/while
# being processed by the Member-3 pipeline. Configurable so Docker /
# production deployments can mount a volume here (Member 4).
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", str(PROJECT_ROOT / "datasets" / "input")))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_UPLOAD_SIZE_BYTES = int(os.getenv("MAX_UPLOAD_SIZE_BYTES", str(50 * 1024 * 1024)))  # 50MB default

DATA_UPLOAD_MAX_MEMORY_SIZE = MAX_UPLOAD_SIZE_BYTES
FILE_UPLOAD_MAX_MEMORY_SIZE = MAX_UPLOAD_SIZE_BYTES

# ─── REST Framework ────────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "common.pagination.DefaultPagination",
    "PAGE_SIZE": 20,
    "EXCEPTION_HANDLER": "common.exceptions.api_exception_handler",
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
    ),
}

# ─── JWT (SimpleJWT) ────────────────────────────────────────────────
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(os.getenv("JWT_ACCESS_MINUTES", "30"))),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(os.getenv("JWT_REFRESH_DAYS", "7"))),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# SimpleJWT's blacklist app is needed for logout-by-blacklisting a refresh
# token and for ROTATE_REFRESH_TOKENS / BLACKLIST_AFTER_ROTATION above.
INSTALLED_APPS.insert(INSTALLED_APPS.index("rest_framework_simplejwt") + 1,
                      "rest_framework_simplejwt.token_blacklist")

# ─── CORS ───────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = _env_list(
    "CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
)
CORS_ALLOW_CREDENTIALS = True

# ─── Logging (basic; Member 4 owns broader infra logging) ───────────
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "root": {
        "handlers": ["console"],
        "level": os.getenv("DJANGO_LOG_LEVEL", "INFO"),
    },
}

# ─── Celery (optional; falls back to an in-process thread if unset) ──
# See apps/processing/services.py — this is a soft dependency. If
# Member 4 wires up a real Celery worker later, set CELERY_BROKER_URL
# and USE_CELERY=true to route processing jobs through it instead.
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "")
USE_CELERY = _env_bool("USE_CELERY", False)