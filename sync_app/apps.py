from django.apps import AppConfig


class SyncAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'sync_app'
    verbose_name = 'مدیریت همگام‌سازی'

    def ready(self):
        from django.conf import settings

        print(f"🔧 راه‌اندازی sync_app - OFFLINE_MODE: {getattr(settings, 'OFFLINE_MODE', False)}")

        # فقط در حالت آفلاین سیگنال‌ها را ثبت کن
        if not getattr(settings, 'OFFLINE_MODE', False):
            print("ℹ️ حالت آنلاین - سیگنال‌های sync_app غیرفعال")
            return

        print("✅ حالت آفلاین - وارد کردن سیگنال‌های sync_app")
        import sync_app.signals  # دقیقاً مانند sync_api