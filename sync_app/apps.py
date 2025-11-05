def ready(self):
    from django.conf import settings

    print(f"🔧 راه‌اندازی sync_app - OFFLINE_MODE: {getattr(settings, 'OFFLINE_MODE', False)}")

    # فقط در حالت آفلاین سیگنال‌ها را ثبت کن
    if not getattr(settings, 'OFFLINE_MODE', False):
        print("ℹ️ حالت آنلاین - سیگنال‌های سینک غیرفعال")
        return

    # سرویس سینک خودکار می‌تواند غیرفعال باشد، اما سیگنال‌های ثبت تغییرات باید فعال باشند
    try:
        import threading
        import time

        def delayed_registration():
            # تاخیر برای اطمینان از لود کامل جنگو
            time.sleep(5)
            from .signals import safe_register_signals
            safe_register_signals()

        thread = threading.Thread(target=delayed_registration, daemon=True)
        thread.start()

        print("✅ سیگنال‌های ثبت تغییرات برای حالت آفلاین فعال شدند")

    except Exception as e:
        print(f"⚠️ خطا در فعال‌سازی سیگنال‌ها: {e}")