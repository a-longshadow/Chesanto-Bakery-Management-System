from django.apps import AppConfig


class AuditConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.audit'
    verbose_name = 'Audit'

    def ready(self):
        # import signal handlers
        try:
            import apps.audit.signals  # noqa: F401
        except Exception:
            pass
