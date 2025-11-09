from django.contrib import admin
from .models import AllowedIP

@admin.register(AllowedIP)
class AllowedIPAdmin(admin.ModelAdmin):
    list_display = ['ip_address', 'description', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['ip_address', 'description']
    list_editable = ['is_active']