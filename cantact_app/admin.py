from django.contrib import admin

from cantact_app.models import accuntmodel,savecodphon,dataacont,phonnambermodel

admin.site.register(accuntmodel)
admin.site.register(savecodphon)
admin.site.register(dataacont)
admin.site.register(phonnambermodel)



# ------------------------------ثبت شعب----------------------------
from django.contrib import admin
from .models import Branch, BranchAdmin


@admin.register(Branch)
class BranchAdminPanel(admin.ModelAdmin):
    list_display = ['name', 'address', 'get_sellers_count']
    filter_horizontal = ['sellers']
    search_fields = ['name', 'address']

    def get_sellers_count(self, obj):
        return obj.sellers.count()

    get_sellers_count.short_description = 'تعداد فروشندگان'


@admin.register(BranchAdmin)
class BranchAdminModelAdmin(admin.ModelAdmin):
    list_display = ['branch', 'admin_user', 'get_admin_name']
    list_filter = ['branch']
    search_fields = ['admin_user__firstname', 'admin_user__lastname', 'branch__name']

    def get_admin_name(self, obj):
        return f"{obj.admin_user.firstname} {obj.admin_user.lastname}"

    get_admin_name.short_description = 'نام مدیر'


    # ---------------------------برسی لاگین ها------------------------------------------


# در admin.py اپ مربوطه

from django.contrib import admin
from cantact_app.models import UserSessionLog


@admin.register(UserSessionLog)
class UserSessionLogAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'device_type',
        'ip_address',
        'login_time',
        'last_activity',
        'is_active'
    ]
    list_filter = ['device_type', 'is_active', 'login_time']
    search_fields = ['user__username', 'ip_address', 'user_agent']
    readonly_fields = ['login_time', 'last_activity']
    actions = ['terminate_sessions']

    def terminate_sessions(self, request, queryset):
        """اکشن برای خاتمه دادن به سشن‌های انتخاب شده"""
        for session_log in queryset:
            session_log.terminate()
        self.message_user(request, f"{queryset.count()} سشن با موفقیت خاتمه یافت.")

    terminate_sessions.short_description = "خاتمه دادن به سشن‌های انتخاب شده"