from django.apps import AppConfig

class PaymentsConfig(AppConfig):  # Renamed for consistency
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'payments'  # Must match your folder name

    def ready(self):
        # Ensure the filename is exactly 'signals.py'
        import payments.signals