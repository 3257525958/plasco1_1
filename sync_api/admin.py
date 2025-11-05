from django.contrib import admin
from .models import ChangeTracker


@admin.register(ChangeTracker)
class ChangeTrackerAdmin(admin.ModelAdmin):
    list_display = [
        'app_name',
        'model_name',
        'record_id',
        'action',
        'changed_at',
        'is_synced'
    ]
    list_filter = [
        'app_name',
        'model_name',
        'action',
        'is_synced',
        'changed_at'
    ]
    search_fields = [
        'app_name',
        'model_name',
        'record_id'
    ]
    readonly_fields = ['changed_at']
    list_per_page = 50
    date_hierarchy = 'changed_at'

    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('app_name', 'model_name', 'record_id', 'action')
        }),
        ('وضعیت سینک', {
            'fields': ('is_synced', 'changed_at')
        }),
    )

    def has_add_permission(self, request):
        """غیرفعال کردن امکان ایجاد دستی"""
        return False

    def has_change_permission(self, request, obj=None):
        """غیرفعال کردن امکان ویرایش"""
        return False