# plasco/__init__.py
import threading
import time
from django.conf import settings

def auto_start_sync_service():
    """شروع خودکار سرویس سینک در حالت آفلاین"""
    if getattr(settings, 'OFFLINE_MODE', False) and getattr(settings, 'SYNC_AUTO_START', True):
        time.sleep(10)  # منتظر بمان تا جنگو کامل لود شود
        try:
            from sync_app.sync_service import sync_service  # ✅ تغییر این خط
            sync_service.start_auto_sync()
            print("✅ سرویس سینک خودکار راه‌اندازی شد")
        except Exception as e:
            print(f"⚠️ خطا در راه‌اندازی سرویس سینک: {e}")

# شروع در تابع جداگانه
try:
    sync_thread = threading.Thread(target=auto_start_sync_service, daemon=True)
    sync_thread.start()
except Exception as e:
    print(f"⚠️ خطا در شروع سرویس سینک: {e}")