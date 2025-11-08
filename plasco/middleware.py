from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.urls import reverse
from .offline_ip_manager import is_allowed_offline_ip, get_client_ip


class ControlPanelMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # اگر کاربر در حال دسترسی به کنترل پنل یا نصب آفلاین هست، اجازه بده
        if (request.path.startswith('/control-panel/') or
                request.path.startswith('/offline/') or
                request.path.startswith('/static/') or
                request.path.startswith('/media/') or
                request.path.startswith('/admin/')):
            return self.get_response(request)

        # اگر IP کاربر مجاز آفلاین هست و هنوز حالت انتخاب نکرده
        if (is_allowed_offline_ip(request) and
                'operation_mode' not in request.session):
            # کاربر رو به کنترل پنل هدایت کن
            return HttpResponseRedirect(reverse('control_panel'))

        response = self.get_response(request)
        return response

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip