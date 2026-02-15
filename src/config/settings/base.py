from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parents[3]
APPS_DIR = BASE_DIR / "src"

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
)

if (BASE_DIR / ".env").exists():
    environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY", default="unsafe-secret-key")
DEBUG = env("DJANGO_DEBUG")

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "drf_spectacular",
    "django_filters",
    "corsheaders",
]

LOCAL_APPS = [
    "apps.common.apps.CommonConfig",
    "apps.users.apps.UsersConfig",
    "apps.frontend.apps.FrontendConfig",
    "apps.facilities.apps.FacilitiesConfig",
    "apps.owners.apps.OwnersConfig",
    "apps.pets.apps.PetsConfig",
    "apps.crm.apps.CrmConfig",
    "apps.visits.apps.VisitsConfig",
    "apps.clinical.apps.ClinicalConfig",
    "apps.labs.apps.LabsConfig",
    "apps.inventory.apps.InventoryConfig",
    "apps.billing.apps.BillingConfig",
    "apps.documents.apps.DocumentsConfig",
    "apps.tasks.apps.TasksConfig",
    "apps.audit.apps.AuditConfig",
    "apps.reports.apps.ReportsConfig",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.audit.middleware.AuditLogMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgres://pettrace:pettrace@localhost:5432/pettrace",
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "ru-ru"
TIME_ZONE = "Europe/Moscow"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "users.User"

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
}

SPECTACULAR_SETTINGS = {
    "TITLE": "PetTrace API",
    "DESCRIPTION": "API for veterinary clinic automation platform.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "ENUM_NAME_OVERRIDES": {
        "ProcedureExecutionStatusEnum": [
            ("PLANNED", "Запланирован"),
            ("IN_PROGRESS", "В работе"),
            ("DONE", "Готово"),
            ("CANCELED", "Отменен"),
        ],
        "TaskLifecycleStatusEnum": [
            ("TODO", "К выполнению"),
            ("IN_PROGRESS", "В работе"),
            ("DONE", "Готово"),
            ("CANCELED", "Отменен"),
        ],
        "CabinetTypeEnum": [
            ("CONSULTATION", "Консультация"),
            ("PROCEDURE", "Процедурный"),
            ("LAB", "Лаборатория"),
            ("SURGERY", "Операционный"),
            ("INPATIENT", "Стационар"),
            ("OTHER", "Другое"),
        ],
    },
}

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])

REDIS_URL = env("REDIS_URL", default="redis://localhost:6379/0")
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    }
}
REPORTS_CACHE_TTL = env.int("REPORTS_CACHE_TTL", default=120)
REPORTS_WARMUP_ENABLED = env.bool("REPORTS_WARMUP_ENABLED", default=True)
REPORTS_WARMUP_DAYS = env.list("REPORTS_WARMUP_DAYS", default=["1", "7", "30"])
REPORTS_WARMUP_INTERVAL_SECONDS = env.int("REPORTS_WARMUP_INTERVAL_SECONDS", default=900)
CRM_DISPATCH_INTERVAL_SECONDS = env.int("CRM_DISPATCH_INTERVAL_SECONDS", default=120)

CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/1")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="redis://localhost:6379/2")
CELERY_TASK_TIME_LIMIT = 60 * 10
CELERY_TASK_SOFT_TIME_LIMIT = 60 * 5
CELERY_BEAT_SCHEDULER = "celery.beat:PersistentScheduler"
CELERY_BEAT_SCHEDULE = {
    "labs.check-sla": {
        "task": "apps.labs.tasks.check_lab_order_sla",
        "schedule": 300,
    },
    "tasks.mark-overdue": {
        "task": "apps.tasks.tasks.mark_overdue_tasks",
        "schedule": 180,
    },
    "notifications.send-pending": {
        "task": "apps.tasks.tasks.send_pending_notifications",
        "schedule": 60,
    },
    "crm.dispatch-due": {
        "task": "apps.crm.tasks.dispatch_due_communications_task",
        "schedule": CRM_DISPATCH_INTERVAL_SECONDS,
    },
    "audit.purge-old": {
        "task": "apps.audit.tasks.purge_audit_logs_task",
        "schedule": 60 * 60 * 24,
    },
}
if REPORTS_WARMUP_ENABLED:
    CELERY_BEAT_SCHEDULE["reports.warm-cache"] = {
        "task": "apps.reports.tasks.warm_reports_cache",
        "schedule": REPORTS_WARMUP_INTERVAL_SECONDS,
    }

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(levelname)s %(asctime)s %(name)s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}
