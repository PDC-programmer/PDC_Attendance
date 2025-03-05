from django.apps import AppConfig


class ApprovalAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'approval_app'

    def ready(self):
        import approval_app.signals  # โหลด signals เมื่อแอปนี้ถูกโหลด
