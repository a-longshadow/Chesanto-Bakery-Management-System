from django.apps import AppConfig


class InventoryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.inventory'
    verbose_name = 'Inventory Management'

    def ready(self):
        """
        Import models to trigger programmatic model generation.
        This ensures all per-item models are registered with Django.
        """
        # Import to trigger model registration
        from . import models  # noqa: F401
