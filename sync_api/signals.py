# sync_api/signals.py - نسخه اصلاح شده
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.conf import settings
from .models import ChangeTracker

print("🔧 [SIGNALS] ماژول signals.py برای sync_api بارگذاری شد")

# لیست مدل‌های مستثنی شده
EXCLUDED_MODELS = [
    'Session', 'ContentType', 'LogEntry', 'Permission',
    'Group', 'Migration', 'Token', 'DataSyncLog',
    'ServerSyncLog', 'SyncToken', 'SyncSession',
    'TokenProxy', 'ChangeTracker'
]

EXCLUDED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',  # ✅ اضافه شد
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'sync_app',
    'sync_api'
]


def should_track_changes(sender, instance):
    """بررسی آیا باید تغییرات این مدل را ردیابی کرد"""
    # فقط در حالت آنلاین پردازش کن
    if getattr(settings, 'OFFLINE_MODE', False):
        return False

    # بررسی اپ و مدل
    if sender._meta.app_label in EXCLUDED_APPS:
        return False

    if sender.__name__ in EXCLUDED_MODELS:
        return False

    # بررسی وجود فیلد id
    if not hasattr(instance, 'id'):
        return False

    return True


@receiver(post_save)
def handle_model_save(sender, instance, created, **kwargs):
    """ردیابی ایجاد و آپدیت - نسخه اصلاح شده"""
    if not should_track_changes(sender, instance):
        return

    try:
        app_label = sender._meta.app_label
        model_name = sender._meta.model_name
        full_model_name = f"{app_label}.{model_name}"

        action = 'create' if created else 'update'

        # سریالایز کردن داده‌ها
        data = {}
        for field in instance._meta.get_fields():
            if not field.is_relation or field.one_to_one:
                try:
                    field_name = field.name
                    value = getattr(instance, field_name)

                    # تبدیل مقادیر برای JSON
                    if value is None:
                        data[field_name] = None
                    elif hasattr(value, 'isoformat'):
                        data[field_name] = value.isoformat()
                    elif isinstance(value, (int, float, bool)):
                        data[field_name] = value
                    else:
                        data[field_name] = str(value)
                except (AttributeError, ValueError):
                    data[field_name] = None

        # ایجاد لاگ
        ChangeTracker.objects.create(
            model_type=full_model_name,
            record_id=instance.id,
            action=action,
            data=data,
            sync_direction='server_to_local',
            app_name=app_label,
            model_name=model_name
        )

        print(f"📝 تغییر ثبت شد (آنلاین): {full_model_name} - ID: {instance.id} - Action: {action}")

    except Exception as e:
        print(f"❌ خطا در پردازش تغییرات برای {sender.__name__}: {e}")


@receiver(post_delete)
def handle_model_delete(sender, instance, **kwargs):
    """ردیابی حذف - نسخه اصلاح شده"""
    if not should_track_changes(sender, instance):
        return

    try:
        app_label = sender._meta.app_label
        model_name = sender._meta.model_name
        full_model_name = f"{app_label}.{model_name}"

        # برای حذف، فقط اطلاعات پایه را ذخیره کن
        ChangeTracker.objects.create(
            model_type=full_model_name,
            record_id=instance.id,
            action='delete',
            data={'id': instance.id, 'model': full_model_name},
            sync_direction='server_to_local',
            app_name=app_label,
            model_name=model_name
        )

        print(f"🗑️ حذف ثبت شد (آنلاین): {full_model_name} - ID: {instance.id}")

    except Exception as e:
        print(f"❌ خطا در پردازش حذف برای {sender.__name__}: {e}")


print("✅ سیگنال‌های sync_api با دکوراتور @receiver ثبت شدند")