from django.apps import AppConfig


class TenantConfig(AppConfig):
    name = 'Tenant'
    
    def ready(self):
        import Tenant.signals
