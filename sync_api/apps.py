# sync_api/apps.py - نسخه اصلاح شده
from django.apps import AppConfig  # ✅ این خط حیاتی است!
import sys


class SyncApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'sync_api'

    def ready(self):
        # اگر در حال اجرای migration هستیم، سیگنال‌ها را فعال نکن
        if 'migrate' in sys.argv or 'makemigrations' in sys.argv:
            print("🔴 حالت migration - سیگنال‌های sync_api غیرفعال")
            return

        from django.conf import settings

        print(f"🔧 راه‌اندازی sync_api - OFFLINE_MODE: {getattr(settings, 'OFFLINE_MODE', False)}")

        # فقط در حالت آنلاین سیگنال‌ها را ثبت کن
        if getattr(settings, 'OFFLINE_MODE', False):
            print("🔴 حالت آفلاین - سیگنال‌های sync_api غیرفعال")
            return

        print("✅ حالت آنلاین - وارد کردن سیگنال‌های sync_api")
        import sync_api.signals