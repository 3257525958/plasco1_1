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

    print("🔧 در حال ثبت سیگنال‌های ردیابی تغییرات برای sync_app...")

    # فقط در حالت آفلاین سیگنال‌ها را ثبت کن
    if not getattr(settings, 'OFFLINE_MODE', False):
        print("ℹ️ حالت آنلاین - سیگنال‌های sync_app غیرفعال")
        return

    print("🎯 فعال‌سازی سیگنال‌های sync_app برای حالت آفلاین...")

    from django.db.models.signals import post_save, post_delete
    from django.apps import apps

    # لیست اپ‌های معاف از ثبت سیگنال
    EXCLUDED_APPS = [
        'django.contrib.admin', 'django.contrib.auth',
        'django.contrib.contenttypes', 'django.contrib.sessions',
        'django.contrib.messages', 'django.contrib.staticfiles',
        'rest_framework', 'rest_framework.authtoken',
        'corsheaders', 'sync_app', 'sync_api'
    ]

    registered_count = 0

    for app_config in apps.get_app_configs():
        app_name = app_config.name

        if any(app_name.startswith(excluded) for excluded in EXCLUDED_APPS):
            continue

        for model in app_config.get_models():
            model_name = model.__name__
            model_key = f"{app_name}.{model_name}"

            try:
                # قطع کردن هر سیگنال قبلی با همین dispatch_uid
                post_save.disconnect(dispatch_uid=f"sync_app_{model_key}_save")
                post_delete.disconnect(dispatch_uid=f"sync_app_{model_key}_delete")
            except:
                pass  # اگر قبلاً ثبت نشده بود، مشکلی نیست

            try:
                # ثبت سیگنال‌های sync_app با dispatch_uid منحصر به فرد
                post_save.connect(
                    handle_model_change,
                    sender=model,
                    weak=False,
                    dispatch_uid=f"sync_app_{model_key}_save"
                )
                post_delete.connect(
                    handle_model_delete,
                    sender=model,
                    weak=False,
                    dispatch_uid=f"sync_app_{model_key}_delete"
                )
                registered_count += 1
                print(f"   ✅ سیگنال sync_app ثبت شد: {model_key}")
            except Exception as e:
                print(f"   ⚠️ خطا در ثبت سیگنال sync_app برای {model_key}: {e}")
                continue

    print(f"🎯 تعداد مدل‌های ثبت شده در sync_app: {registered_count}")


def handle_model_change(sender, instance, created, **kwargs):
    """مدیریت تغییرات مدل‌ها برای سیستم آفلاین"""
    try:
        from django.conf import settings
        if not getattr(settings, 'OFFLINE_MODE', False):
            return

        from sync_app.models import DataSyncLog

        app_label = instance._meta.app_label
        model_name = instance._meta.model_name
        full_model_name = f"{app_label}.{model_name}"

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

        print(f"📝 تغییر ثبت شد (آفلاین): {full_model_name} - ID: {instance.id} - Action: {action}")

    except Exception as e:
        print(f"❌ خطا در پردازش تغییرات برای {sender.__name__}: {e}")


def handle_model_delete(sender, instance, **kwargs):
    """مدیریت حذف مدل‌ها برای سیستم آفلاین"""
    try:
        from django.conf import settings
        if not getattr(settings, 'OFFLINE_MODE', False):
            return

        from sync_app.models import DataSyncLog

        app_label = instance._meta.app_label
        model_name = instance._meta.model_name
        full_model_name = f"{app_label}.{model_name}"

        # برای حذف، فقط اطلاعات پایه را ذخیره کن
        DataSyncLog.objects.create(
            model_type=full_model_name,
            record_id=instance.id,
            action='delete',
            data={'id': instance.id, 'model': full_model_name},
            sync_direction='local_to_server',
            app_name=app_label,
            model_name=model_name
        )

        print(f"🗑️ حذف ثبت شد (آفلاین): {full_model_name} - ID: {instance.id}")

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