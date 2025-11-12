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
    """ایجاد پکیج نصب کامل و مستقل"""
    try:
        BASE_DIR = settings.BASE_DIR

        # ایجاد بافر ZIP در حافظه
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            print("📦 ایجاد پکیج نصب کامل و مستقل...")

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

            # فایل settings_offline.py با تمام تنظیمات
            settings_content = f'''
"""
Django settings for plasco project - OFFLINE MODE
ایجاد شده در: {timezone.now().strftime("%Y/%m/%d %H:%M")}
IPهای مجاز: {selected_ips}
"""

from pathlib import Path
import os
import sys

BASE_DIR = Path(__file__).resolve().parent.parent

# اضافه کردن مسیر اپ‌ها به sys.path
sys.path.append(str(BASE_DIR))

IS_OFFLINE_MODE = True
SECRET_KEY = 'django-insecure-plasco-offline-2024-secret-key'
DEBUG = True

ALLOWED_HOSTS = {selected_ips} + ['localhost', '127.0.0.1']

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

# غیرفعال کردن چک‌های سیستم
SILENCED_SYSTEM_CHECKS = ['security.W004', 'security.W008', 'security.W009']
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
mysqlclient==2.1.1
'''
            zipf.writestr('requirements_offline.txt', requirements_content)

            # فایل batch اصلی - کاملاً هوشمند
            bat_content = f'''@echo off
chcp 65001
title Plasco Offline System - Auto Installer

setlocal EnableDelayedExpansion

echo.
echo ================================================
echo      Plasco Offline System - Auto Installer
echo ================================================
echo.

echo 📅 Created: {timezone.now().strftime("%Y/%m/%d %H:%M")}
echo 🔐 Allowed IPs: {', '.join(selected_ips)}
echo.

:CHECK_PYTHON
echo [1/6] 🔍 Checking Python installation...
python --version >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Python is installed
    goto :INSTALL_REQUIREMENTS
)

echo ❌ Python not found!
echo.
echo 📥 Installing Python automatically...
echo.

# دانلود و نصب پایتون به صورت خودکار
set PYTHON_URL=https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe
set PYTHON_INSTALLER=python_installer.exe

echo 🔄 Downloading Python 3.10.11...
powershell -Command "Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%PYTHON_INSTALLER%'"

if exist %PYTHON_INSTALLER% (
    echo 🚀 Installing Python...
    start /wait %PYTHON_INSTALLER% /quiet InstallAllUsers=1 PrependPath=1
    del %PYTHON_INSTALLER%

    echo ✅ Python installed successfully!
    timeout /t 3 /nobreak >nul
) else (
    echo ❌ Failed to download Python installer
    echo 📝 Please install Python manually from: https://python.org
    pause
    exit /b 1
)

:INSTALL_REQUIREMENTS
echo.
echo [2/6] 📦 Installing Python packages...
pip install --upgrade pip
pip install -r requirements_offline.txt

if %errorlevel% neq 0 (
    echo ⚠️ Some packages failed to install, continuing...
)

:CREATE_DATABASE
echo.
echo [3/6] 🗃️ Creating database...
python manage.py migrate

:CREATE_SUPERUSER
echo.
echo [4/6] 👤 Creating admin user...
python manage.py shell -c "
from django.contrib.auth import get_user_model;
User = get_user_model();
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@plasco.local', 'admin123');
    print('✅ Admin user created: admin / admin123');
else:
    print('ℹ️ Admin user already exists');
"

:START_SERVER
echo.
echo [5/6] 🚀 Starting Plasco Offline System...
echo.
echo 🌐 ACCESS URLs:
echo    http://localhost:8000
echo    http://127.0.0.1:8000
'''

            for ip in selected_ips:
                bat_content += f'echo    http://{ip}:8000\n'

            bat_content += f'''
echo.
echo 🔧 Admin Panel: http://localhost:8000/admin
echo 👤 Username: admin
echo 🔑 Password: admin123
echo.
echo ⏰ Please wait, server is starting...
echo.

:START
python manage.py runserver 0.0.0.0:8000

if %errorlevel% neq 0 (
    echo.
    echo ❌ Server stopped with error!
    echo 🔧 Attempting to fix common issues...

    echo 🔄 Running migrations again...
    python manage.py migrate

    echo 🔄 Collecting static files...
    python manage.py collectstatic --noinput

    echo 🚀 Restarting server...
    goto :START
)

echo.
echo ✅ Server stopped normally
pause
'''

            zipf.writestr('start_server.bat', bat_content)

            # فایل batch جایگزین ساده
            simple_bat = '''@echo off
chcp 65001
title Plasco - Simple Start

echo.
echo Starting Plasco Offline System...
echo.
echo If Python is not installed, please install it from:
echo https://www.python.org/downloads/
echo.
echo Then run start_server.bat
echo.
pause
'''
            zipf.writestr('README_FIRST.bat', simple_bat)

            # فایل راهنمای کامل
            readme_content = f'''
Plasco Offline System - Complete Installation Guide
==================================================

Created: {timezone.now().strftime("%Y/%m/%d %H:%M")}
Allowed IPs: {', '.join(selected_ips)}

📋 QUICK START:
1. Extract ALL files to a folder
2. Run "start_server.bat" as Administrator
3. Wait for automatic installation
4. Open browser and go to: http://localhost:8000

🔧 DETAILED INSTRUCTIONS:

A) AUTOMATIC INSTALLATION (Recommended):
   ------------------------------------
   1. Run "start_server.bat" as Administrator
   2. The system will automatically:
      - Install Python (if not present)
      - Install all required packages
      - Create database
      - Create admin user
      - Start the server

B) MANUAL INSTALLATION:
   -------------------
   1. Install Python 3.8+ from https://python.org
   2. Run "start_server.bat"
   3. Or run these commands manually:
      pip install -r requirements_offline.txt
      python manage.py migrate
      python manage.py runserver 0.0.0.0:8000

🌐 ACCESS INFORMATION:
   - Main System: http://localhost:8000
   - Admin Panel: http://localhost:8000/admin
   - Username: admin
   - Password: admin123

📞 SUPPORT:
   If you encounter any issues:
   1. Make sure all files are extracted
   2. Run as Administrator
   3. Check if Python is installed
   4. Contact IT support

⚙️ SYSTEM REQUIREMENTS:
   - Windows 7/8/10/11
   - 500MB free space
   - Internet connection (for first-time setup)

🔐 SECURITY NOTE:
   This system will only work on these IP addresses:
   {', '.join(selected_ips)}
'''
            zipf.writestr('README.txt', readme_content.strip())

            # فایل پیکربندی اضافی
            config_content = f'''
[Plasco_Offline_System]
version=1.0
created={timezone.now().strftime("%Y-%m-%d %H:%M:%S")}
allowed_ips={','.join(selected_ips)}
admin_username=admin
admin_password=admin123
database=sqlite
port=8000
'''
            zipf.writestr('plasco_config.ini', config_content.strip())

        zip_buffer.seek(0)
        print("✅ پکیج نصب کامل ایجاد شد")
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
            response['Content-Disposition'] = 'attachment; filename="plasco_offline_complete.zip"'

            return response

        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'خطا در ایجاد فایل نصب: {str(e)}'
            })

    return JsonResponse({'status': 'error', 'message': 'متد غیرمجاز'})

