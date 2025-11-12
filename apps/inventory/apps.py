from django.apps import AppConfig


class InventoryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.inventory'
    
    # PHASE 1 REFACTORING: Signals disabled - moved to explicit utility functions
    # def ready(self):
    #     """Import signals when app is ready"""
    #     import apps.inventory.signals
