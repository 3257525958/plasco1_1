# sync_app/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db import transaction
from django.utils import timezone
from .models import DataSyncLog
import time

print("🔧 سیگنال‌های سینک کامل فعال شدند")

# ایجاد یک دیکشنری برای پیگیری تغییرات اخیر
_recent_changes = {}


def should_create_sync_log(instance):
    """بررسی آیا باید برای این instance لاگ سینک ایجاد کرد"""
    # اگر instance فیلد id نداشته باشد (مثل Session)، لاگ ایجاد نکن
    if not hasattr(instance, 'id'):
        return False

    # اگر از سینک سرور آمده، لاگ ایجاد نکن
    if getattr(instance, '_from_sync', False):
        return False

    # اگر مدل از sync_app هست، لاگ ایجاد نکن
    if instance._meta.app_label == 'sync_app':
        return False

    # اگر مدل‌های سیستمی Django است، لاگ ایجاد نکن
    excluded_models = [
        'Session', 'ContentType', 'LogEntry', 'Permission',
        'Group', 'Migration', 'Token', 'DataSyncLog',
        'ServerSyncLog', 'SyncToken', 'SyncSession',
        'TokenProxy', 'ChangeTracker'
    ]

    if instance.__class__.__name__ in excluded_models:
        return False

    # اپ‌های سیستمی Django را حذف کن
    excluded_apps = [
        'django.contrib.admin',
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.messages',
        'django.contrib.staticfiles',
        'rest_framework',
        'rest_framework.authtoken',
        'corsheaders',
        'sync_api'
    ]

    if instance._meta.app_label in excluded_apps:
        return False

    # 🚨 بسیار مهم: اگر اخیراً پردازش شده، لاگ ایجاد نکن
    instance_key = f"{instance._meta.app_label}.{instance.__class__.__name__}.{instance.id}"
    if instance_key in _recent_changes:
        timestamp = _recent_changes[instance_key]
        if time.time() - timestamp < 30:  # ۳۰ ثانیه
            return False

    return True


def mark_as_recently_processed(instance):
    """علامت‌گذاری instance به عنوان پردازش شده اخیر"""
    if not hasattr(instance, 'id'):
        return
    instance_key = f"{instance._meta.app_label}.{instance.__class__.__name__}.{instance.id}"
    _recent_changes[instance_key] = time.time()


@receiver(post_save)
def on_model_save(sender, instance, created, **kwargs):
    """سیگنال برای ذخیره سازی مدل‌ها - برای تمام مدل‌ها"""

    def create_log_after_commit():
        if not should_create_sync_log(instance):
            return

        try:
            # تعیین action
            action = 'create' if created else 'update'

            # 🚨 بررسی آیا قبلاً لاگ مشابهی وجود دارد
            existing_log = DataSyncLog.objects.filter(
                app_name=sender._meta.app_label,
                model_name=sender.__name__,
                record_id=instance.id,
                sync_status=False,
                sync_direction='local_to_server'
            ).exists()

            if existing_log:
                print(f"⏭️ لاگ تکراری وجود دارد: {sender._meta.app_label}.{sender.__name__}-{instance.id}")
                return

            # ایجاد DataSyncLog
            DataSyncLog.objects.create(
                app_name=sender._meta.app_label,
                model_name=sender.__name__,
                record_id=instance.id,
                action=action,
                data={},
                sync_status=False,
                sync_direction='local_to_server'
            )
            print(
                f"📝 تغییر ثبت شد (آفلاین): {sender._meta.app_label}.{sender.__name__} - ID: {instance.id} - Action: {action}")

            # علامت‌گذاری به عنوان پردازش شده
            mark_as_recently_processed(instance)
        except Exception as e:
            print(f"❌ خطا در ثبت تغییر: {e}")

    transaction.on_commit(create_log_after_commit)


@receiver(post_delete)
def on_model_delete(sender, instance, **kwargs):
    """سیگنال برای حذف مدل‌ها - برای تمام مدل‌ها"""

    def create_delete_log_after_commit():
        if not should_create_sync_log(instance):
            return

        try:
            DataSyncLog.objects.create(
                app_name=sender._meta.app_label,
                model_name=sender.__name__,
                record_id=instance.id,
                action='delete',
                data={},
                sync_status=False,
                sync_direction='local_to_server'
            )
            print(f"📝 حذف ثبت شد (آفلاین): {sender._meta.app_label}.{sender.__name__} - ID: {instance.id}")

            # علامت‌گذاری به عنوان پردازش شده
            mark_as_recently_processed(instance)
        except Exception as e:
            print(f"❌ خطا در ثبت حذف: {e}")

    transaction.on_commit(create_delete_log_after_commit)