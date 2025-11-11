# sync_api/apps.py - نسخه کامل و ایمن
from django.apps import AppConfig
import sys


class SyncApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'sync_api'
    verbose_name = 'همگام‌سازی API'

    def ready(self):
        """
        راه‌اندازی سیگنال‌ها با مدیریت خطا و شرایط مختلف
        """
        try:
            # غیرفعال کردن در حالت‌های مدیریتی خطرناک
            dangerous_commands = [
                'clearsessions', 'flush', 'shell',
                'migrate', 'makemigrations', 'test'
            ]

            if any(cmd in sys.argv for cmd in dangerous_commands):
                print("🔴 حالت مدیریت - سیگنال‌های sync_api غیرفعال")
                return

            # غیرفعال کردن در حالت migration
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

            # ایمپورت سیگنال‌ها با مدیریت خطا
            try:
                import sync_api.signals
                print("✅ سیگنال‌های sync_api با موفقیت بارگذاری شدند")
            except Exception as e:
                print(f"⚠️ خطا در بارگذاری سیگنال‌ها: {e}")

        except Exception as e:
            print(f"⚠️ خطا در راه‌اندازی sync_api: {e}")