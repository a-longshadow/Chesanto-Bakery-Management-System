from django.apps import AppConfig


class ProductionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.production'
    verbose_name = 'Production Management'
    
    def ready(self):
        """Import signals when app is ready"""
        import apps.production.signals
