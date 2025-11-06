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

    # تغییر به CharField ساده بدون محدودیت
    model_type = models.CharField(max_length=100)  # مثلا: 'account_app.Product'
    record_id = models.BigIntegerField()  # تغییر به BigInteger برای پشتیبانی از IDهای بزرگ
    action = models.CharField(max_length=10)  # create, update, delete
    data = models.JSONField(null=True, blank=True)
    sync_direction = models.CharField(max_length=20, choices=SYNC_DIRECTIONS, default='local_to_server')
    sync_status = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    synced_at = models.DateTimeField(null=True, blank=True)
    conflict_resolved = models.BooleanField(default=False)
    error_message = models.TextField(blank=True)

    # اضافه کردن فیلدهای جدید برای مدیریت بهتر
    app_name = models.CharField(max_length=50, blank=True)  # نام اپ
    model_name = models.CharField(max_length=50, blank=True)  # نام مدل
    branch_id = models.IntegerField(null=True, blank=True)  # برای تفکیک شعبه
    last_sync_timestamp = models.DateTimeField(null=True, blank=True, help_text="آخرین زمان سینک موفق")
    batch_id = models.CharField(max_length=100, blank=True, help_text="شناسه دسته برای ردیابی")
    is_full_sync = models.BooleanField(default=False, help_text="آیا سینک کامل بوده است؟")

    class Meta:
        # db_table = 'sync_api_changetracker'  # تغییر نام جدول برای جلوگیری از تداخل
        indexes = [
            models.Index(fields=['sync_status', 'model_type']),
            models.Index(fields=['app_name', 'model_name']),
            models.Index(fields=['created_at']),
            models.Index(fields=['last_sync_timestamp', 'model_type']),
            models.Index(fields=['batch_id']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.model_type} - {self.record_id} - {self.action}"

    def save(self, *args, **kwargs):
        # استخراج خودکار app_name و model_name از model_type
        if self.model_type and '.' in self.model_type and not self.app_name:
            parts = self.model_type.split('.')
            if len(parts) == 2:
                self.app_name, self.model_name = parts
        super().save(*args, **kwargs)