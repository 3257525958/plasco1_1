from django.apps import AppConfig
import sys


class SyncAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'sync_app'
    verbose_name = 'مدیریت همگام‌سازی'

    def ready(self):
        # اگر در حال اجرای migration هستیم، سیگنال‌ها را فعال نکن
        if 'migrate' in sys.argv or 'makemigrations' in sys.argv:
            print("🔴 حالت migration - سیگنال‌های sync_app غیرفعال")
            return

        from django.conf import settings

        print(f"🔧 راه‌اندازی sync_app - OFFLINE_MODE: {getattr(settings, 'OFFLINE_MODE', False)}")

        # فقط در حالت آفلاین سیگنال‌ها را ثبت کن
        if not getattr(settings, 'OFFLINE_MODE', False):
            print("ℹ️ حالت آنلاین - سیگنال‌های سینک غیرفعال")
            return

        print("✅ حالت آفلاین - وارد کردن سیگنال‌های sync_app")
        import sync_app.signals