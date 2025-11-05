from django.apps import AppConfig


class SyncApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'sync_api'

    def ready(self):
        from django.conf import settings

        print(f"🔧 راه‌اندازی sync_api - OFFLINE_MODE: {getattr(settings, 'OFFLINE_MODE', False)}")

        # فقط در حالت آنلاین سیگنال‌ها را ثبت کن
        if getattr(settings, 'OFFLINE_MODE', False):
            print("🔴 حالت آفلاین - سیگنال‌های sync_api غیرفعال")
            return

        try:
            import sync_api.signals
            print("✅ سیگنال‌های sync_api برای حالت آنلاین فعال شدند")
        except Exception as e:
            print(f"⚠️ خطا در فعال‌سازی سیگنال‌های sync_api: {e}")