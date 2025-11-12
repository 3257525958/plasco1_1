from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.conf import settings
from .models import AllowedIP
import json
import zipfile
import io
import os
from pathlib import Path


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


def create_complete_install_package(selected_ips):
    """ایجاد پکیج نصب کامل و کاملاً خودکار"""
    try:
        BASE_DIR = settings.BASE_DIR

        # ایجاد بافر ZIP در حافظه
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            print("📦 ایجاد پکیج نصب کامل و خودکار...")

            # فایل‌های اصلی
            essential_files = [
                'manage.py',
                'plasco/__init__.py',
                'plasco/urls.py',
                'plasco/wsgi.py'
            ]

            # اضافه کردن فایل‌های اصلی
            for file in essential_files:
                file_path = BASE_DIR / file
                if file_path.exists():
                    zipf.write(file_path, file)
                    print(f"✅ اضافه شد: {file}")

            # اضافه کردن پوشه اپ‌ها
            app_folders = [
                'account_app', 'dashbord_app', 'cantact_app', 'invoice_app',
                'it_app', 'pos_payment', 'sync_app', 'sync_api',
                'control_panel', 'offline_ins', 'home_app', 'ip_manager'
            ]

            for app in app_folders:
                app_path = BASE_DIR / app
                if app_path.exists():
                    for root, dirs, files in os.walk(app_path):
                        for file in files:
                            if file.endswith(('.py', '.html', '.css', '.js', '.json', '.txt')):
                                file_path = os.path.join(root, file)
                                arcname = os.path.relpath(file_path, BASE_DIR)
                                zipf.write(file_path, arcname)
                    print(f"✅ اپ {app} اضافه شد")

            # اضافه کردن پوشه templates
            templates_path = BASE_DIR / 'templates'
            if templates_path.exists():
                for root, dirs, files in os.walk(templates_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, BASE_DIR)
                        zipf.write(file_path, arcname)
                print("✅ پوشه templates اضافه شد")

            # اضافه کردن پوشه static
            static_path = BASE_DIR / 'static'
            if static_path.exists():
                for root, dirs, files in os.walk(static_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, BASE_DIR)
                        zipf.write(file_path, arcname)
                print("✅ پوشه static اضافه شد")

            # ==================== فایل‌های ضروری برای نصب آسان ====================

            # فایل settings_offline.py
            settings_content = f'''
"""
Django settings for plasco project - OFFLINE MODE
IPهای مجاز: {selected_ips}
"""

from pathlib import Path
import os
import sys

BASE_DIR = Path(__file__).resolve().parent.parent

IS_OFFLINE_MODE = True
SECRET_KEY = 'django-insecure-plasco-offline-auto-install-2024'
DEBUG = True

ALLOWED_HOSTS = {selected_ips} + ['localhost', '127.0.0.1', '0.0.0.0']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third party
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
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
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

LANGUAGE_CODE = 'fa-ir'
TIME_ZONE = 'Asia/Tehran'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
MEDIA_URL = '/media/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
OFFLINE_MODE = True

# تنظیمات برای نصب آسان
SILENCED_SYSTEM_CHECKS = ['security.W004', 'security.W008']
'''

            zipf.writestr('plasco/settings_offline.py', settings_content.strip())
            zipf.writestr('plasco/settings.py', 'from .settings_offline import *\n')

            # فایل requirements کامل
            requirements_content = '''Django==4.2.7
django-cors-headers==4.3.1
djangorestframework==3.14.0
Pillow==10.0.1
requests==2.31.0
jdatetime==4.1.1
python-barcode==0.15.1
'''
            zipf.writestr('requirements_offline.txt', requirements_content)

            # فایل BAT اصلی - کاملاً اصلاح شده
            main_bat = '''@echo off
chcp 65001
title Plasco Offline System - Auto Installer

REM تغییر به مسیر فایل جاری
cd /d "%~dp0"

echo.
echo ============================================
echo    Plasco Offline System - Auto Installer
echo ============================================
echo.

echo 📍 Current directory:
cd
echo.

echo 🔍 Step 1: Checking Python installation...
python --version
if %errorlevel% neq 0 (
    echo.
    echo ❌ ERROR: Python not found or not in PATH!
    echo.
    echo 📥 Please install Python from:
    echo https://www.python.org/downloads/
    echo.
    echo 💡 IMPORTANT: During installation, check "Add Python to PATH"
    echo.
    echo Press any key to exit...
    pause >nul
    exit /b 1
)

echo ✅ Python is installed
echo.

echo 📦 Step 2: Installing required packages...
pip install -r requirements_offline.txt
if %errorlevel% neq 0 (
    echo.
    echo ⚠️ WARNING: Some packages failed to install
    echo Trying to continue anyway...
    echo.
)

echo 🗃️ Step 3: Setting up database...
python manage.py migrate
if %errorlevel% neq 0 (
    echo.
    echo ❌ ERROR: Database setup failed!
    echo.
    echo Press any key to exit...
    pause >nul
    exit /b 1
)

echo 👤 Step 4: Creating admin user...
python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('admin', 'admin@plasco.com', 'admin123') if not User.objects.filter(username='admin').exists() else print('Admin user already exists')"

echo.
echo 🚀 Step 5: Starting Plasco Offline System...
echo.
echo ============================================
echo    SYSTEM IS READY!
echo ============================================
echo.
echo 🌐 ACCESS URLs:
echo    Main System: http://localhost:8000
echo    Admin Panel: http://localhost:8000/admin
echo.
echo 🔐 ADMIN CREDENTIALS:
echo    Username: admin
echo    Password: admin123
echo.
echo ⏰ Server is starting...
echo ⏹️  To stop server, press CTRL+C
echo ============================================
echo.

python manage.py runserver 0.0.0.0:8000

echo.
echo Server stopped. Press any key to close...
pause >nul
'''
            zipf.writestr('START_HERE.bat', main_bat)

            # فایل BAT جایگزین برای خطایابی
            debug_bat = '''@echo off
chcp 65001
title Plasco Debug Mode

cd /d "%~dp0"

echo.
echo ============================================
echo    Plasco Debug Mode - خطایابی
echo ============================================
echo.

echo 📍 مسیر جاری:
cd
echo.

echo 🔍 بررسی پایتون:
python --version
if %errorlevel% neq 0 (
    echo ❌ پایتون پیدا نشد!
    goto :error
)

echo ✅ پایتون نصب است
echo.

echo 📦 بررسی pip:
pip --version
if %errorlevel% neq 0 (
    echo ❌ pip پیدا نشد!
    goto :error
)

echo ✅ pip نصب است
echo.

echo 🗂️ لیست فایل‌ها:
dir
echo.

echo 🚀 اجرای سیستم...
echo.
START_HERE.bat
goto :end

:error
echo.
echo ❌ مشکل تشخیص داده شد!
echo.
echo 📝 راه‌حل:
echo 1. پایتون را از python.org دانلود کنید
echo 2. هنگام نصب، تیک "Add Python to PATH" را بزنید
echo 3. دوباره تلاش کنید
echo.
pause

:end
'''
            zipf.writestr('DEBUG_MODE.bat', debug_bat)

            # فایل راهنمای کامل
            readme_content = f'''
Plasco Offline System - راهنمای نصب
===================================

📋 روش نصب (ساده):
1. تمام فایل‌ها را در یک پوشه Extract کنید
2. روی فایل "START_HERE.bat" دابل کلیک کنید
3. منتظر بمانید تا سیستم راه‌اندازی شود

🔧 اگر مشکل داشتید:
- فایل "DEBUG_MODE.bat" را اجرا کنید
- یا دستی این دستورات را در CMD اجرا کنید:
  1. python --version
  2. pip install -r requirements_offline.txt
  3. python manage.py migrate
  4. python manage.py runserver 0.0.0.0:8000

🌐 آدرس‌های دسترسی:
- سیستم اصلی: http://localhost:8000
- پنل مدیریت: http://localhost:8000/admin
- کاربر: admin
- رمز: admin123

📞 پشتیبانی:
در صورت مشکل، اطلاعات خطا را ذخیره کرده و با پشتیبانی تماس بگیرید.

🖥️ IPهای مجاز: {', '.join(selected_ips)}
📅 ایجاد شده: {timezone.now().strftime("%Y/%m/%d %H:%M")}
'''
            zipf.writestr('README_FIRST.txt', readme_content)

        zip_buffer.seek(0)
        print("✅ پکیج نصب کامل و خودکار ایجاد شد")
        return zip_buffer

    except Exception as e:
        print(f"❌ خطا در ایجاد پکیج: {str(e)}")
        import traceback
        print(f"❌ جزئیات: {traceback.format_exc()}")
        return None


@csrf_exempt
def create_offline_installer(request):
    """ایجاد و دانلود فایل نصب کامل"""
    if request.method == 'POST':
        try:
            selected_ips_json = request.POST.get('selected_ips', '[]')
            selected_ips = json.loads(selected_ips_json)

            if not selected_ips:
                return JsonResponse({
                    'status': 'error',
                    'message': 'لطفاً حداقل یک IP انتخاب کنید'
                })

            zip_buffer = create_complete_install_package(selected_ips)

            if not zip_buffer:
                return JsonResponse({
                    'status': 'error',
                    'message': 'خطا در ایجاد فایل نصب'
                })

            response = HttpResponse(
                zip_buffer.getvalue(),
                content_type='application/zip'
            )
            response['Content-Disposition'] = 'attachment; filename="plasco_offline_system.zip"'

            return response

        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'خطا در ایجاد فایل نصب: {str(e)}'
            })

    return JsonResponse({'status': 'error', 'message': 'متد غیرمجاز'})


