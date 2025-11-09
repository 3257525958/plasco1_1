from django.http import HttpResponseRedirect
from django.urls import reverse
from .offline_ip_manager import is_allowed_offline_ip, get_client_ip
import logging

logger = logging.getLogger(__name__)

# class ControlPanelMiddleware:
#     def __init__(self, get_response):
#         self.get_response = get_response
#
#     def __call__(self, request):
#         client_ip = get_client_ip(request)
#
#         # لاگ برای دیباگ
#         logger.info(f"🔄 Middleware - IP: {client_ip}, Path: {request.path}")
#         logger.info(f"🔄 Session operation_mode: {request.session.get('operation_mode', 'NOT_SET')}")
#         logger.info(f"🔄 Is allowed IP: {is_allowed_offline_ip(request)}")
#
#         # اگر کاربر در حال دسترسی به کنترل پنل، نصب آفلاین یا فایل‌های استاتیک هست، اجازه بده
#         if (request.path.startswith('/control-panel/') or
#                 request.path.startswith('/offline/') or
#                 request.path.startswith('/static/') or
#                 request.path.startswith('/media/') or
#                 request.path.startswith('/admin/') or
#                 request.path.startswith('/api/')):
#             logger.info(f"✅ اجازه دسترسی مستقیم به: {request.path}")
#             return self.get_response(request)
#
#         # اگر کاربر به صفحه اصلی میاد (/) و IP مجاز هست و هنوز حالت انتخاب نکرده
#         # اگر کاربر به صفحه اصلی میاد (/) و IP مجاز هست
#         # اگر کاربر به صفحه اصلی میاد (/) و IP مجاز هست و هنوز آفلاین نصب نکرده
#         if (request.path == '/' and
#                 is_allowed_offline_ip(request) and
#                 not request.session.get('offline_installed', False)):
#
#             logger.info("🔄 هدایت به کنترل پنل از صفحه اصلی")
#             # کاربر رو به کنترل پنل هدایت کن
#             return HttpResponseRedirect(reverse('control_panel'))
#
#         response = self.get_response(request)
#         return response
#
#     def get_client_ip(self, request):
#         x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
#         if x_forwarded_for:
#             ip = x_forwarded_for.split(',')[0]
#         else:
#             ip = request.META.get('REMOTE_ADDR')
#         return ip
class ControlPanelMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        client_ip = get_client_ip(request)

        # دیباگ ساده
        print(f"🔴 میدلور - IP: {client_ip}, مسیر: {request.path}")
        print(f"🔴 آیا مجازه: {is_allowed_offline_ip(request)}")

        # مستقیماً همه رو به کنترل پنل هدایت کن (موقتاً)
        if request.path == '/':
            print(f"🔴 هدایت همه به کنترل پنل - IP: {client_ip}")
            return HttpResponseRedirect('/control-panel/')

        return self.get_response(request)