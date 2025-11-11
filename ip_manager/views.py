from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from .models import AllowedIP
import json
import zipfile
import io
from pathlib import Path


# توابع مدیریت IPها
def manage_ips(request):
    """صفحه مدیریت IPها"""
    return render(request, 'ip_manager/manage_ips.html')


@csrf_exempt
def list_ips(request):
    """دریافت لیست IPها (API)"""
    try:
        ips = AllowedIP.objects.all().order_by('-created_at')
        ip_list = []

        for ip in ips:
            ip_list.append({
                'id': ip.id,
                'ip_address': ip.ip_address,
                'description': ip.description,
                'is_active': ip.is_active,
                'created_at': ip.created_at.strftime('%Y/%m/%d %H:%M')
            })

        return JsonResponse({'status': 'success', 'ips': ip_list})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


@csrf_exempt
def add_ip(request):
    """افزودن IP جدید (API)"""
    if request.method == 'POST':
        try:
            ip_address = request.POST.get('ip_address')
            description = request.POST.get('description', '')

            if not ip_address:
                return JsonResponse({'status': 'error', 'message': 'آدرس IP الزامی است'})

            if AllowedIP.objects.filter(ip_address=ip_address).exists():
                return JsonResponse({'status': 'error', 'message': 'این IP قبلاً ثبت شده است'})

            allowed_ip = AllowedIP.objects.create(
                ip_address=ip_address,
                description=description
            )

            return JsonResponse({
                'status': 'success',
                'message': 'IP با موفقیت اضافه شد',
                'id': allowed_ip.id
            })

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'خطا در افزودن IP: {str(e)}'})
    else:
        return JsonResponse({'status': 'error', 'message': 'متد غیرمجاز'})


@csrf_exempt
def delete_ip(request, ip_id):
    """حذف IP (API)"""
    try:
        ip = get_object_or_404(AllowedIP, id=ip_id)
        ip.delete()
        return JsonResponse({'status': 'success', 'message': 'IP با موفقیت حذف شد'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'خطا در حذف IP: {str(e)}'})


@csrf_exempt
def update_ip(request, ip_id):
    """ویرایش IP (API)"""
    if request.method == 'POST':
        try:
            ip = get_object_or_404(AllowedIP, id=ip_id)
            ip_address = request.POST.get('ip_address')
            description = request.POST.get('description', '')

            if AllowedIP.objects.filter(ip_address=ip_address).exclude(id=ip_id).exists():
                return JsonResponse({'status': 'error', 'message': 'این IP قبلاً ثبت شده است'})

            ip.ip_address = ip_address
            ip.description = description
            ip.save()

            return JsonResponse({'status': 'success', 'message': 'IP با موفقیت ویرایش شد'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'خطا در ویرایش IP: {str(e)}'})
    else:
        return JsonResponse({'status': 'error', 'message': 'متد غیرمجاز'})


@csrf_exempt
def toggle_ip(request, ip_id):
    """فعال/غیرفعال کردن IP (API)"""
    if request.method == 'POST':
        try:
            ip = get_object_or_404(AllowedIP, id=ip_id)
            action = request.POST.get('action')

            if action == 'activate':
                ip.is_active = True
                message = 'IP با موفقیت فعال شد'
            elif action == 'deactivate':
                ip.is_active = False
                message = 'IP با موفقیت غیرفعال شد'
            else:
                return JsonResponse({'status': 'error', 'message': 'عمل نامعتبر'})

            ip.save()
            return JsonResponse({'status': 'success', 'message': message})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'خطا در تغییر وضعیت IP: {str(e)}'})
    else:
        return JsonResponse({'status': 'error', 'message': 'متد غیرمجاز'})


@csrf_exempt
def create_offline_installer(request):
    """ایجاد و دانلود مستقیم فایل نصب - بدون نیاز به media serving"""
    print("🎯 درخواست ایجاد فایل نصب دریافت شد")

    if request.method == 'POST':
        try:
            # دریافت IPهای انتخاب شده
            selected_ips_json = request.POST.get('selected_ips', '[]')
            selected_ips = json.loads(selected_ips_json)

            print(f"🔢 IPهای دریافت شده: {selected_ips}")

            # ایجاد فایل ZIP در memory
            zip_buffer = io.BytesIO()

            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # فایل README
                readme_content = f'''
Plasco Offline Installer
========================

ایجاد شده در: {timezone.now().strftime("%Y/%m/%d %H:%M")}
IPهای مجاز: {', '.join(selected_ips)}

📋 دستورالعمل نصب:

1. تمام فایل‌ها را در یک پوشه Extract کنید
2. فایل start_windows.bat را اجرا کنید
3. سیستم به صورت خودکار راه‌اندازی می‌شود
4. مرورگر را باز کرده و به آدرس زیر بروید:
   http://localhost:8000

⚙️ نیازمندی‌ها:
- Python 3.8 یا بالاتر
- دسترسی به اینترنت برای نصب اولیه کتابخانه‌ها

📞 پشتیبانی:
در صورت بروز مشکل با واحد فناوری اطلاعات تماس بگیرید.

🔐 اطلاعات امنیتی:
این نسخه فقط برای IPهای زیر قابل دسترسی است:
{', '.join(selected_ips)}
'''

                # فایل start_windows.bat
                bat_content = f'''@echo off
chcp 65001
title Plasco Offline System - Installer

echo.
echo ========================================
echo    Plasco Offline System Installer
echo ========================================
echo.
echo 📅 تاریخ ایجاد: {timezone.now().strftime("%Y/%m/%d")}
echo 🔐 IPهای مجاز: {', '.join(selected_ips)}
echo.

echo 🔍 در حال بررسی نصب Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ❌ خطا: Python بر روی سیستم یافت نشد!
    echo.
    echo 📥 لطفا Python 3.8 یا بالاتر را از آدرس زیر دانلود و نصب کنید:
    echo https://www.python.org/downloads/
    echo.
    echo 💡 هنگام نصب، گزینه "Add Python to PATH" را حتما انتخاب کنید.
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version 2^>^&1') do set python_version=%%i
echo ✅ %python_version% تشخیص داده شد
echo.

echo 📦 در حال نصب کتابخانه‌های مورد نیاز...
pip install -r requirements_offline.txt

if %errorlevel% neq 0 (
    echo.
    echo ⚠️ خطا در نصب کتابخانه‌ها
    echo 🔧 در حال تلاش مجدد با upgrade pip...
    python -m pip install --upgrade pip
    pip install -r requirements_offline.txt
)

echo.
echo 🚀 در حال راه‌اندازی سرور آفلاین پلاسکو...
echo.
echo 🌐 آدرس دسترسی: http://localhost:8000
echo 🌐 آدرس شبکه: http://192.168.1.172:8000
echo 🔐 IPهای مجاز: {', '.join(selected_ips)}
echo.
echo ⏰ لطفا منتظر بمانید...
echo.

python manage.py runserver 0.0.0.0:8000 --settings=plasco.settings_offline

echo.
echo ⚠️ سرور متوقف شد
pause
'''

                # فایل requirements_offline.txt
                requirements_content = '''Django==4.2.7
django-cors-headers==4.3.1
djangorestframework==3.14.0
Pillow==10.0.1
requests==2.31.0
mysqlclient==2.1.1
'''

                # فایل settings_offline.py
                settings_content = f'''
"""
Django settings for plasco project - OFFLINE MODE
Generated: {timezone.now().strftime("%Y/%m/%d %H:%M")}
Allowed IPs: {selected_ips}
"""

from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-offline-{int(timezone.now().timestamp())}'
DEBUG = True
ALLOWED_HOSTS = {selected_ips}

print("🟢 اجرا در حالت آفلاین")
print("🔐 IPهای مجاز: {', '.join(selected_ips)}")

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third party apps
    'rest_framework',
    'corsheaders',

    # Local apps
    'account_app',
    'dashbord_app',
    'cantact_app',
    'invoice_app',
    'it_app',
    'pos_payment',
    'sync_app',
    'sync_api',
    'control_panel',
    'offline_ins',
    'ip_manager',
    'home_app',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'corsheaders.middleware.CorsMiddleware',
]

ROOT_URLCONF = 'plasco.urls'

TEMPLATES = [
    {{
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {{
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        }},
    }},
]

WSGI_APPLICATION = 'plasco.wsgi.application'

DATABASES = {{
    'default': {{
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db_offline.sqlite3',
    }}
}}

AUTH_PASSWORD_VALIDATORS = [
    {{
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    }},
    {{
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    }},
    {{
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    }},
    {{
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    }},
]

LANGUAGE_CODE = 'fa-ir'
TIME_ZONE = 'Asia/Tehran'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
MEDIA_URL = '/media/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# تنظیمات اختصاصی
OFFLINE_MODE = True
SYNC_DISABLED = True

# تنظیمات REST Framework
REST_FRAMEWORK = {{
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ]
}}

# تنظیمات CORS
CORS_ALLOWED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://192.168.1.172:8000",
]

CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True
'''

                # فایل manage.py
                manage_content = '''#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'plasco.settings_offline')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
'''

                # فایل __init__.py برای پوشه plasco
                init_content = '''# Plasco Offline Package'''

                # فایل urls.py اصلی
                urls_content = '''
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('home_app.urls')),
    path('control-panel/', include('control_panel.urls')),
    path('offline/install/', include('offline_ins.urls')),
    path('cantact/', include('cantact_app.urls')),
    path('dashbord/', include('dashbord_app.urls')),
    path('account/', include('account_app.urls')),
    path('invoice/', include('invoice_app.urls')),
    path('it/', include('it_app.urls')),
    path('pos-payment/', include('pos_payment.urls')),
    path('api/sync/', include('sync_api.urls')),
    path('sync_app/', include('sync_app.urls')),
    path('ip/', include('ip_manager.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
'''

                # اضافه کردن تمام فایل‌ها به ZIP
                zipf.writestr('README.txt', readme_content)
                zipf.writestr('start_windows.bat', bat_content)
                zipf.writestr('requirements_offline.txt', requirements_content)
                zipf.writestr('plasco/__init__.py', init_content)
                zipf.writestr('plasco/settings_offline.py', settings_content)
                zipf.writestr('plasco/urls.py', urls_content)
                zipf.writestr('plasco/wsgi.py',
                              '"""\nWSGI config for plasco project.\n"""\nimport os\nfrom django.core.wsgi import get_wsgi_application\nos.environ.setdefault("DJANGO_SETTINGS_MODULE", "plasco.settings_offline")\napplication = get_wsgi_application()')
                zipf.writestr('manage.py', manage_content)

                print("✅ تمام فایل‌ها به ZIP اضافه شدند")

            # برگرداندن فایل به عنوان response
            zip_buffer.seek(0)
            response = HttpResponse(
                zip_buffer.getvalue(),
                content_type='application/zip'
            )
            response[
                'Content-Disposition'] = f'attachment; filename="plasco_offline_installer_{int(timezone.now().timestamp())}.zip"'

            file_size = len(zip_buffer.getvalue())
            print(f"🚀 فایل برای دانلود ارسال شد - حجم: {file_size} بایت")

            return response

        except Exception as e:
            print(f"❌ خطا در ایجاد فایل: {str(e)}")
            import traceback
            print(f"❌ جزئیات خطا: {traceback.format_exc()}")

            return JsonResponse({
                'status': 'error',
                'message': f'خطا در ایجاد فایل نصب: {str(e)}'
            })

    return JsonResponse({'status': 'error', 'message': 'لطفاً از POST استفاده کنید'})