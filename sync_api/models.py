# در sync_api/models.py این را اضافه کنید:
from django.db import models


class ChangeTracker(models.Model):
    app_name = models.CharField(max_length=50)
    model_name = models.CharField(max_length=50)
    record_id = models.BigIntegerField()
    action = models.CharField(max_length=10)  # create, update, delete
    changed_at = models.DateTimeField(auto_now_add=True)
    is_synced = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=['app_name', 'model_name', 'is_synced']),
            models.Index(fields=['changed_at']),
        ]

    def __str__(self):
        return f"{self.app_name}.{self.model_name} - {self.record_id} - {self.action}"


