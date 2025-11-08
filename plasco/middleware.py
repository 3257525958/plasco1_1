from django.http import HttpResponseRedirect
from django.urls import reverse
from .offline_ip_manager import is_allowed_offline_ip, get_client_ip


class ControlPanelMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # اگر کاربر در حال دسترسی به کنترل پنل، نصب آفلاین یا فایل‌های استاتیک هست، اجازه بده
        if (request.path.startswith('/control-panel/') or
                request.path.startswith('/offline/') or
                request.path.startswith('/static/') or
                request.path.startswith('/media/') or
                request.path.startswith('/admin/') or
                request.path.startswith('/api/')):
            return self.get_response(request)

        # اگر کاربر به صفحه اصلی میاد (/) و IP مجاز هست و هنوز حالت انتخاب نکرده
        if (request.path == '/' and
                is_allowed_offline_ip(request) and
                'operation_mode' not in request.session):
            # کاربر رو به کنترل پنل هدایت کن
            return HttpResponseRedirect(reverse('control_panel'))

        response = self.get_response(request)
        return response