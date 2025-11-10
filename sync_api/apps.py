class SyncApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'sync_api'

    def ready(self):
        import sys

        # 🚨 لیست دستوراتی که سیگنال‌ها باید غیرفعال باشند
        dangerous_commands = [
            'clearsessions', 'flush', 'shell',
            'migrate', 'makemigrations', 'test'
        ]

        if any(cmd in sys.argv for cmd in dangerous_commands):
            print("🔴 حالت مدیریت - سیگنال‌های sync_api غیرفعال")
            return

        from django.conf import settings
        print(f"🔧 راه‌اندازی sync_api - OFFLINE_MODE: {getattr(settings, 'OFFLINE_MODE', False)}")

        # فقط در حالت آنلاین سیگنال‌ها را ثبت کن
        if getattr(settings, 'OFFLINE_MODE', False):
            print("🔴 حالت آفلاین - سیگنال‌های sync_api غیرفعال")
            return

        print("✅ حالت آنلاین - وارد کردن سیگنال‌های sync_api")
        import sync_api.signals