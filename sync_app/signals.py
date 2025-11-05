from django.db.models.signals import post_save, post_delete, post_migrate
from django.dispatch import receiver
from django.apps import apps
from django.conf import settings
import time

# دیکشنری برای پیگیری مدل‌های ثبت شده
_registered_models = {}


def safe_register_signals():
    """ثبت ایمن سیگنال‌ها - فقط در حالت آفلاین"""
    from django.conf import settings

    print("🔧 در حال ثبت سیگنال‌های ردیابی تغییرات...")

    # فقط در حالت آفلاین سیگنال‌ها را ثبت کن
    if not getattr(settings, 'OFFLINE_MODE', False):
        print("ℹ️ حالت آنلاین - سیگنال‌های ثبت تغییرات غیرفعال")
        return

    # بقیه کد ثبت سیگنال‌ها...
def handle_model_change(sender, instance, created, **kwargs):
    """مدیریت تغییرات مدل‌ها"""
    try:
        if not getattr(settings, 'OFFLINE_MODE', False):
            return

        from sync_app.models import DataSyncLog

        app_label = instance._meta.app_label
        model_name = instance._meta.model_name
        full_model_name = f"{app_label}.{model_name}"

        print(f"🔔 سیگنال فعال: تغییر در {full_model_name} - ID: {instance.id}")
        action = 'create' if created else 'update'

        # سریالایز کردن داده‌ها
        data = serialize_instance(instance)

        # ایجاد لاگ
        DataSyncLog.objects.create(
            model_type=full_model_name,
            record_id=instance.id,
            action=action,
            data=data,
            sync_direction='local_to_server',
            app_name=app_label,
            model_name=model_name
        )

        if kwargs.get('raw', False):  # جلوگیری از سینک در فیکسچرها
            return

        print(f"📝 تغییر ثبت شد: {full_model_name} - ID: {instance.id} - Action: {action}")

    except Exception as e:
        print(f"❌ خطا در پردازش تغییرات برای {sender.__name__}: {e}")


def handle_model_delete(sender, instance, **kwargs):
    """مدیریت حذف مدل‌ها"""
    try:
        if not getattr(settings, 'OFFLINE_MODE', False):
            return

        from sync_app.models import DataSyncLog

        app_label = instance._meta.app_label
        model_name = instance._meta.model_name
        full_model_name = f"{app_label}.{model_name}"

        DataSyncLog.objects.create(
            model_type=full_model_name,
            record_id=instance.id,
            action='delete',
            data={'id': instance.id, 'model': full_model_name},
            sync_direction='local_to_server',
            app_name=app_label,
            model_name=model_name
        )

        print(f"🗑️ حذف ثبت شد: {full_model_name} - ID: {instance.id}")

    except Exception as e:
        print(f"❌ خطا در پردازش حذف برای {sender.__name__}: {e}")


def serialize_instance(instance):
    """سریالایز کردن ایمن آبجکت"""
    data = {}

    for field in instance._meta.get_fields():
        if not field.is_relation or field.one_to_one:
            try:
                field_name = field.name
                value = getattr(instance, field_name)
                data[field_name] = convert_value_for_json(value)
            except (AttributeError, ValueError, Exception) as e:
                data[field_name] = None

    return data


def convert_value_for_json(value):
    """تبدیل مقادیر برای ذخیره در JSON"""
    if value is None:
        return None
    elif hasattr(value, 'isoformat'):  # DateTime/Date
        return value.isoformat()
    elif isinstance(value, (int, float, bool)):
        return value
    elif hasattr(value, '__str__'):
        return str(value)
    else:
        return None


# سیگنال برای ثبت پس از مهاجرت
@receiver(post_migrate)
def register_signals_after_migrate(sender, **kwargs):
    """ثبت سیگنال‌ها پس از اتمام مهاجرت"""
    safe_register_signals()

