# signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db import transaction
from .models import ChangeTracker, DataSyncLog
import json


@receiver(post_save, sender=ChangeTracker)
def create_data_sync_log_from_change_tracker(sender, instance, created, **kwargs):
    """
    ایجاد خودکار DataSyncLog از ChangeTracker
    دقیقاً مشابه منطق sync_app
    """
    if created and not instance.is_synced:
        try:
            with transaction.atomic():
                # ایجاد رکورد متناظر در DataSyncLog
                sync_log = DataSyncLog.objects.create(
                    model_type=f"{instance.app_name}.{instance.model_name}",
                    record_id=instance.record_id,
                    action=instance.action,
                    data={},  # داده‌های اضافی اگر نیاز باشد
                    sync_direction='local_to_server',  # یا بر اساس منطق شما
                    sync_status=False,
                    app_name=instance.app_name,
                    model_name=instance.model_name,
                    branch_id=None,  # می‌توانید از settings بگیرید
                    batch_id=f"change_tracker_{instance.id}",
                    is_full_sync=False,
                    error_message=""  # مقدار پیش‌فرض برای خطا
                )

                # علامت‌گذاری ChangeTracker به عنوان سینک شده
                instance.is_synced = True
                instance.save(update_fields=['is_synced'])

                print(f"DataSyncLog created for ChangeTracker {instance.id}")

        except Exception as e:
            print(f"Error creating DataSyncLog: {str(e)}")
            # در صورت خطا، is_synced را false نگه می‌داریم تا مجدداً تلاش شود
            instance.is_synced = False
            instance.save(update_fields=['is_synced'])