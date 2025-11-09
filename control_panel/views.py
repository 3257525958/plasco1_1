from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import logging
from plasco.offline_ip_manager import is_allowed_offline_ip, get_client_ip

logger = logging.getLogger(__name__)


def control_panel(request):
    """صفحه کنترل پنل برای انتخاب حالت اجرا"""
    client_ip = get_client_ip(request)

    # لاگ برای دیباگ
    logger.info(f"🎯 کنترل پنل - IP: {client_ip}")
    logger.info(f"🎯 Is allowed: {is_allowed_offline_ip(request)}")

    if not is_allowed_offline_ip(request):
        # اگر IP مجاز نبود، مستقیماً به حالت آنلاین هدایت شود
        logger.warning(f"🚫 دسترسی غیرمجاز به کنترل پنل از IP: {client_ip}")
        request.session['operation_mode'] = 'online'
        return redirect('/')  # به صفحه اصلی هدایت شود

    logger.info(f"✅ نمایش کنترل پنل برای IP: {client_ip}")
    context = {
        'client_ip': client_ip,
    }
    return render(request, 'control_panel/control_panel.html', context)