from django.db import models
from django.utils import timezone


class DataSyncLog(models.Model):
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
        db_table = 'data_sync_log'
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


class SyncSession(models.Model):
    SYNC_STATUS_CHOICES = [
        ('in_progress', 'در حال انجام'),
        ('completed', 'تکمیل شده'),
        ('failed', 'ناموفق'),
        ('partial', 'ناقص'),
    ]

    session_id = models.CharField(max_length=100, unique=True)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    records_synced = models.IntegerField(default=0)
    records_total = models.IntegerField(default=0)
    sync_direction = models.CharField(max_length=20, choices=DataSyncLog.SYNC_DIRECTIONS)
    status = models.CharField(max_length=20, choices=SYNC_STATUS_CHOICES, default='in_progress')
    error_message = models.TextField(blank=True)

    # اضافه کردن فیلدهای جدید
    sync_type = models.CharField(max_length=20, default='auto', choices=[
        ('auto', 'خودکار'),
        ('manual', 'دستی'),
        ('forced', 'اجباری')
    ])
    duration_seconds = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = 'sync_sessions'
        ordering = ['-start_time']

    def save(self, *args, **kwargs):
        if self.end_time and self.start_time:
            self.duration_seconds = (self.end_time - self.start_time).total_seconds()
        super().save(*args, **kwargs)


class OfflineSetting(models.Model):
    setting_key = models.CharField(max_length=100, unique=True)
    setting_value = models.TextField()
    description = models.TextField(blank=True)
    last_sync = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    data_type = models.CharField(max_length=20, default='string', choices=[
        ('string', 'متنی'),
        ('integer', 'عددی'),
        ('boolean', 'بولین'),
        ('json', 'JSON')
    ])

    class Meta:
        db_table = 'offline_settings'
        verbose_name = 'تنظیمات آفلاین'
        verbose_name_plural = 'تنظیمات آفلاین'

    def __str__(self):
        return self.setting_key

    def get_value(self):
        """تبدیل مقدار به نوع صحیح"""
        if self.data_type == 'integer':
            return int(self.setting_value)
        elif self.data_type == 'boolean':
            return self.setting_value.lower() in ['true', '1', 'yes']
        elif self.data_type == 'json':
            import json
            return json.loads(self.setting_value)
        return self.setting_value


class ServerSyncLog(models.Model):
    # استفاده از model_type بدون محدودیت
    model_type = models.CharField(max_length=100)
    record_id = models.BigIntegerField()
    action = models.CharField(max_length=10)
    data = models.JSONField()
    source_ip = models.GenericIPAddressField()
    sync_direction = models.CharField(max_length=20, choices=[
        ('local_to_server', 'لوکال به سرور'),
        ('server_to_local', 'سرور به لوکال')
    ])
    created_at = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    # اضافه کردن فیلدهای جدید
    app_name = models.CharField(max_length=50, blank=True)
    model_name = models.CharField(max_length=50, blank=True)
    retry_count = models.IntegerField(default=0)

    class Meta:
        db_table = 'server_sync_log'
        indexes = [
            models.Index(fields=['processed', 'created_at']),
        ]

    def save(self, *args, **kwargs):
        if self.model_type and '.' in self.model_type and not self.app_name:
            parts = self.model_type.split('.')
            if len(parts) == 2:
                self.app_name, self.model_name = parts
        super().save(*args, **kwargs)


# در sync_app/models.py
# در sync_app/models.py
# class ChangeTracker(models.Model):
#     app_name = models.CharField(max_length=50)
#     model_name = models.CharField(max_length=50)
#     record_id = models.BigIntegerField()
#     action = models.CharField(max_length=10)  # create, update, delete
#     changed_at = models.DateTimeField(auto_now_add=True)
#     is_synced = models.BooleanField(default=False)
#
#     class Meta:
#         indexes = [
#             models.Index(fields=['app_name', 'model_name', 'is_synced']),
#             models.Index(fields=['changed_at']),
#         ]
#
#     def __str__(self):
#         return f"{self.app_name}.{self.model_name} - {self.record_id} - {self.action}"

