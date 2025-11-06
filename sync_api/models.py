# در sync_api/models.py این را اضافه کنید:
from django.db import models

# models.py
from django.db import models
from django.db import transaction


from django.db import models

from django.db import models

class ChangeTracker(models.Model):
    SYNC_DIRECTIONS = [
        ('local_to_server', 'لوکال به سرور'),
        ('server_to_local', 'سرور به لوکال'),
    ]

    model_type = models.CharField(max_length=100)
    record_id = models.BigIntegerField()
    action = models.CharField(max_length=10)
    data = models.JSONField(null=True, blank=True)
    sync_direction = models.CharField(max_length=20, choices=SYNC_DIRECTIONS, default='local_to_server')
    sync_status = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    synced_at = models.DateTimeField(null=True, blank=True)
    conflict_resolved = models.BooleanField(default=False)
    error_message = models.TextField(blank=True)

    # فیلدهای اضافی
    app_name = models.CharField(max_length=50, blank=True)
    model_name = models.CharField(max_length=50, blank=True)
    branch_id = models.IntegerField(null=True, blank=True)
    last_sync_timestamp = models.DateTimeField(null=True, blank=True, help_text="آخرین زمان سینک موفق")
    batch_id = models.CharField(max_length=100, blank=True, help_text="شناسه دسته برای ردیابی")
    is_full_sync = models.BooleanField(default=False, help_text="آیا سینک کامل بوده است؟")

    class Meta:
        # کامنت کردن خط زیر - استفاده از نام پیش‌فرض Django
        # db_table = 'change_tracker'
        indexes = [
            models.Index(fields=['sync_status', 'model_type']),
            models.Index(fields=['app_name', 'model_name']),
            models.Index(fields=['created_at']),
            models.Index(fields=['last_sync_timestamp', 'model_type']),
            models.Index(fields=['batch_id']),
        ]
        ordering = ['-created_at']