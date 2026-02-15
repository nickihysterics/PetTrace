from django.apps import AppConfig


class ClinicalConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.clinical"
    verbose_name = "Клинические протоколы"

    def ready(self):
        from . import signals  # noqa: F401
