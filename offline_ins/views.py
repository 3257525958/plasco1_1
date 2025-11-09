from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import os
import subprocess
import sqlite3
from pathlib import Path
import shutil
from django.conf import settings
from plasco.offline_ip_manager import is_allowed_offline_ip, get_client_ip, add_allowed_ip
import logging
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import os
import subprocess
import sqlite3
from pathlib import Path
import shutil
from django.conf import settings
from plasco.offline_ip_manager import is_allowed_offline_ip, get_client_ip, add_allowed_ip

# این خط باید حتماً وجود داشته باشد
logger = logging.getLogger(__name__)

def offline_install(request):
    """صفحه نصب آفلاین"""
    if not is_allowed_offline_ip(request):
        return redirect('/')

    context = {
        'client_ip': get_client_ip(request),
        'installation_steps': [
            'بررسی سیستم',
            'افزودن IP به لیست مجاز',
            'ایجاد دیتابیس SQLite',
            'پیکربندی تنظیمات آفلاین',
            'اتمام نصب'
        ]
    }
    return render(request, 'offline_ins/install.html', context)


@csrf_exempt
def install_step(request):
    """اجرای مرحله به مرحله نصب"""
    if not is_allowed_offline_ip(request):
        return JsonResponse({'status': 'error', 'message': 'دسترسی غیرمجاز'})

    step = request.POST.get('step', '1')
    client_ip = get_client_ip(request)

    try:
        if step == '1':
            # مرحله 1: بررسی سیستم
            return check_system()

        elif step == '2':
            # مرحله 2: افزودن IP به لیست مجاز
            return add_ip_to_allowed(client_ip)

        elif step == '3':
            # مرحله 3: ایجاد دیتابیس SQLite
            return create_offline_database()

        elif step == '4':
            # مرحله 4: پیکربندی تنظیمات آفلاین
            return setup_offline_settings()

        elif step == '5':
            # مرحله 5: اتمام نصب
            return finish_installation(request)

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'خطا در مرحله نصب: {str(e)}'
        })


def check_system():
    """بررسی سیستم"""
    # بررسی وجود پوشه‌های لازم
    required_dirs = ['static', 'media', 'templates']
    for dir_name in required_dirs:
        dir_path = Path(__file__).resolve().parent.parent.parent / dir_name
        if not dir_path.exists():
            os.makedirs(dir_path)

    return JsonResponse({
        'status': 'success',
        'message': 'سیستم بررسی شد و آماده نصب است',
        'next_step': '2'
    })


def add_ip_to_allowed(client_ip):
    """افزودن IP به لیست مجاز"""
    add_allowed_ip(client_ip)

    return JsonResponse({
        'status': 'success',
        'message': f'IP {client_ip} به لیست مجاز اضافه شد',
        'next_step': '3'
    })


def create_offline_database():
    """ایجاد دیتابیس SQLite"""
    try:
        BASE_DIR = Path(__file__).resolve().parent.parent
        db_path = BASE_DIR / 'db_offline.sqlite3'

        # اگر دیتابیس قدیمی وجود دارد، پاک شود
        if db_path.exists():
            os.remove(db_path)

        # ایجاد دیتابیس جدید
        conn = sqlite3.connect(db_path)
        conn.close()

        # اجرای migrations برای ایجاد جداول
        try:
            subprocess.run([
                'python', 'manage.py', 'migrate',
                '--settings=plasco.settings_offline'
            ], capture_output=True, text=True, timeout=60)
        except:
            pass  # اگر اجرا نشد، بعداً دستی انجام می‌شود

        return JsonResponse({
            'status': 'success',
            'message': 'دیتابیس آفلاین ایجاد شد',
            'next_step': '4'
        })

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'خطا در ایجاد دیتابیس: {str(e)}'
        })


def setup_offline_settings():
    """پیکربندی تنظیمات آفلاین"""
    try:
        # ایجاد فایل settings_offline.py اگر وجود ندارد
        BASE_DIR = Path(__file__).resolve().parent.parent
        settings_offline_path = BASE_DIR / 'plasco' / 'settings_offline.py'

        if not settings_offline_path.exists():
            # کپی از settings اصلی با تغییرات آفلاین
            with open(BASE_DIR / 'plasco' / 'settings.py', 'r', encoding='utf-8') as f:
                content = f.read()

            # اعمال تغییرات برای حالت آفلاین
            content = content.replace("IS_OFFLINE_MODE = False", "IS_OFFLINE_MODE = True")
            content = content.replace("DEBUG = False", "DEBUG = True")
            content = content.replace("OFFLINE_MODE = False", "OFFLINE_MODE = True")

            # تغییر دیتابیس به SQLite
            db_config = """
# دیتابیس SQLite برای حالت آفلاین
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db_offline.sqlite3',
    }
}
"""
            # پیدا کردن بخش DATABASES و جایگزینی
            import re
            content = re.sub(
                r"DATABASES = \{.*?\n\}",
                db_config,
                content,
                flags=re.DOTALL
            )

            with open(settings_offline_path, 'w', encoding='utf-8') as f:
                f.write(content)

        return JsonResponse({
            'status': 'success',
            'message': 'تنظیمات آفلاین پیکربندی شد',
            'next_step': '5'
        })

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'خطا در پیکربندی تنظیمات: {str(e)}'
        })


def finish_installation(request):
    logger = logging.getLogger(__name__)  # این خط را اضافه کنید اگر نیست
    """اتمام نصب"""
    client_ip = get_client_ip(request)

    # علامت گذاری که نصب کامل شده
    request.session['offline_installed'] = True
    request.session['operation_mode'] = 'offline'

    logger.info(f"✅ نصب آفلاین کامل شد برای IP: {client_ip}")

    return JsonResponse({
        'status': 'success',
        'message': 'نصب سیستم آفلاین با موفقیت завер شد!',
        'redirect': '/offline/success/'  # به صفحه موفقیت هدایت شود
    })


def offline_success(request):
    """صفحه موفقیت نصب"""
    return render(request, 'offline_ins/success.html', {
        'client_ip': get_client_ip(request)
    })