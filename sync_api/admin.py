from django.contrib import admin
from .models import ChangeTracker

@admin.register(ChangeTracker)
class ChangeTrackerAdmin(admin.ModelAdmin):
    list_display = [
        'app_name',
        'model_name',
        'record_id',
        'action',
        'sync_direction',
        'sync_status',
        'created_at'  # تغییر از changed_at به created_at
    ]
    list_filter = [
        'app_name',
        'model_name',
        'action',
        'sync_status',
        'sync_direction',
        'created_at'  # تغییر از changed_at به created_at
    ]
    search_fields = [
        'app_name',
        'model_name',
        'record_id',
        'batch_id'
    ]
    readonly_fields = ['created_at']  # تغییر از changed_at به created_at
    list_per_page = 50
    date_hierarchy = 'created_at'  # تغییر از changed_at به created_at

    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('app_name', 'model_name', 'record_id', 'action', 'sync_direction')
        }),
        ('وضعیت سینک', {
            'fields': ('sync_status', 'created_at', 'synced_at', 'conflict_resolved')
        }),
        ('داده‌ها', {
            'fields': ('data', 'error_message', 'batch_id')
        }),
    )

    def has_add_permission(self, request):
        """غیرفعال کردن امکان ایجاد دستی"""
        return False

    def has_change_permission(self, request, obj=None):
        """غیرفعال کردن امکان ویرایش"""
        return False