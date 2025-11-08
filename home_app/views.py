from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from cantact_app.models import accuntmodel
from django.contrib.auth import authenticate,login, logout
from django.contrib.auth.models import User
from django.shortcuts import redirect
profilestatus =['']

def home_def(request):
    login_user = 'false'
    if request.user.is_authenticated:
        login_user = 'true'
        us = accuntmodel.objects.all()
        for u in us:
            if u.melicode == request.user.username:
                profilestatus[0] = f"{u.firstname} {u.lastname}  "

    return render(request,'new_home.html',context={
                                                                'login_user':login_user,
                                                                 'profilestatus':profilestatus[0],
                                                                })

def logute(request):
    logout(request)
    return redirect('/')


# ---------------------------نصب آفلاین آنلاین---------------------------------------------------

from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.conf import settings
import socket
import json
import os


def detect_installation(request):
    """صفحه تشخیص و راه‌اندازی اولیه"""
    # دریافت IP کاربر
    client_ip = get_client_ip(request)

    # بررسی آیا IP در لیست مجاز است
    allowed_ips = getattr(settings, 'OFFLINE_ALLOWED_IPS', [])

    if client_ip not in allowed_ips:
        # اگر IP مجاز نیست، به صفحه اصلی برو
        return redirect('home')

    context = {
        'client_ip': client_ip,
        'allowed_ips': allowed_ips
    }

    return render(request, 'home_app/installation_detection.html', context)


def get_client_ip(request):
    """دریافت IP واقعی کاربر"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


@csrf_exempt
def check_offline_installation(request):
    """بررسی آیا سیستم آفلاین نصب شده است"""
    if request.method == 'POST':
        data = json.loads(request.body)
        client_ip = data.get('client_ip')

        # اینجا می‌توانید بررسی کنید آیا سیستم نصب شده
        # برای تست، همیشه False برمی‌گردانیم
        is_installed = False

        return JsonResponse({
            'status': 'success',
            'is_installed': is_installed,
            'client_ip': client_ip
        })

    return JsonResponse({'status': 'error', 'message': 'متد غیرمجاز'})


@csrf_exempt
def start_offline_installation(request):
    """شروع فرآیند نصب آفلاین"""
    if request.method == 'POST':
        data = json.loads(request.body)
        client_ip = data.get('client_ip')

        try:
            # ایجاد فایل راهنما برای نصب
            installation_data = {
                'client_ip': client_ip,
                'server_url': settings.ONLINE_SERVER_URL,
                'timestamp': time.time(),
                'step': 0,
                'status': 'started'
            }

            # ذخیره اطلاعات نصب
            install_file = os.path.join(settings.BASE_DIR, f'install_{client_ip}.json')
            with open(install_file, 'w', encoding='utf-8') as f:
                json.dump(installation_data, f, ensure_ascii=False)

            return JsonResponse({
                'status': 'success',
                'message': 'فرآیند نصب شروع شد',
                'next_step': 1
            })

        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'خطا در شروع نصب: {str(e)}'
            })

    return JsonResponse({'status': 'error', 'message': 'متد غیرمجاز'})

