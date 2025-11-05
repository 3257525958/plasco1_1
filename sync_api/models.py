# در sync_api/models.py این را اضافه کنید:
from django.db import models

# models.py
from django.db import models
from django.db import transaction


class ChangeTracker(models.Model):
    ACTIONS = [
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
    ]

    app_name = models.CharField(max_length=50)
    model_name = models.CharField(max_length=50)
    record_id = models.BigIntegerField()
    action = models.CharField(max_length=10, choices=ACTIONS)
    changed_at = models.DateTimeField(auto_now_add=True)
    is_synced = models.BooleanField(default=False)

    # فیلدهای اضافی برای مدیریت بهتر
    sync_attempts = models.IntegerField(default=0)
    last_sync_error = models.TextField(blank=True, null=True)
    should_retry = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=['app_name', 'model_name', 'is_synced']),
            models.Index(fields=['changed_at']),
            models.Index(fields=['is_synced', 'should_retry']),  # برای queryهای بهینه
        ]
        ordering = ['-changed_at']

    def __str__(self):
        return f"{self.app_name}.{self.model_name} - {self.record_id} - {self.action}"

    def mark_as_synced(self):
        """علامت‌گذاری به عنوان سینک شده"""
        self.is_synced = True
        self.sync_attempts += 1
        self.last_sync_error = ""
        self.save(update_fields=['is_synced', 'sync_attempts', 'last_sync_error'])

    def mark_as_failed(self, error_message):
        """علامت‌گذاری به عنوان ناموفق"""
        self.is_synced = False
        self.sync_attempts += 1
        self.last_sync_error = error_message
        self.should_retry = self.sync_attempts < 3  # فقط ۳ بار تلاش مجاز
        self.save(update_fields=['is_synced', 'sync_attempts', 'last_sync_error', 'should_retry'])