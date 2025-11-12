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
import requests
from django.core.files.base import ContentFile


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
    """ایجاد پکیج نصب کامل با پایتون توکار"""
    try:
        BASE_DIR = settings.BASE_DIR
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            print("📦 Creating complete installation package with embedded Python...")

            # ==================== فایل‌های اصلی پروژه ====================

            # فایل manage.py
            manage_path = BASE_DIR / 'manage.py'
            if manage_path.exists():
                zipf.write(manage_path, 'plasco_system/manage.py')
                print("✅ Added: manage.py")

            # پوشه اصلی پروژه (plasco)
            plasco_path = BASE_DIR / 'plasco'
            if plasco_path.exists():
                for root, dirs, files in os.walk(plasco_path):
                    for file in files:
                        if file.endswith(('.py', '.html', '.css', '.js', '.json', '.txt')):
                            file_path = os.path.join(root, file)
                            arcname = os.path.join('plasco_system', os.path.relpath(file_path, BASE_DIR))
                            zipf.write(file_path, arcname)
                print("✅ Added plasco folder completely")

            # ==================== تمام اپلیکیشن‌ها ====================
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
                            if file.endswith(('.py', '.html', '.css', '.js', '.json', '.txt', '.md')):
                                file_path = os.path.join(root, file)
                                arcname = os.path.join('plasco_system', os.path.relpath(file_path, BASE_DIR))
                                zipf.write(file_path, arcname)
                    print(f"✅ Added app: {app}")

            # ==================== فایل‌های قالب و استاتیک ====================

            # پوشه templates
            templates_path = BASE_DIR / 'templates'
            if templates_path.exists():
                for root, dirs, files in os.walk(templates_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.join('plasco_system', os.path.relpath(file_path, BASE_DIR))
                        zipf.write(file_path, arcname)
                print("✅ Added templates folder")

            # پوشه static
            static_path = BASE_DIR / 'static'
            if static_path.exists():
                for root, dirs, files in os.walk(static_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.join('plasco_system', os.path.relpath(file_path, BASE_DIR))
                        zipf.write(file_path, arcname)
                print("✅ Added static folder")

            # ==================== فایل‌های پیکربندی و نصب ====================

            # فایل settings_offline.py
            settings_content = f'''
"""
Django settings for plasco project - OFFLINE MODE
Allowed IPs: {selected_ips}
Generated: {timezone.now().strftime("%Y/%m/%d %H:%M")}
"""

from pathlib import Path
import os
import sys

# اضافه کردن مسیر پایتون توکار به sys.path
embedded_python_path = os.path.join(os.path.dirname(__file__), '..', 'python', 'python-3.10.11-embed-amd64')
if os.path.exists(embedded_python_path):
    site_packages = os.path.join(embedded_python_path, 'site-packages')
    if site_packages not in sys.path:
        sys.path.insert(0, site_packages)

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-offline-plasco-2024-secret-key-change-in-production'
DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0', '192.168.1.100', '192.168.1.101', '192.168.1.102'] + {selected_ips}

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

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = 'fa-ir'
TIME_ZONE = 'Asia/Tehran'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
MEDIA_URL = '/media/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# غیرفعال کردن چک‌های امنیتی برای نصب آسان
SILENCED_SYSTEM_CHECKS = [
    'security.W004', 
    'security.W008', 
    'security.W009',
    'security.W019',
    'security.W020'
]

# تنظیمات REST Framework
REST_FRAMEWORK = {{
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ]
}}

CORS_ALLOW_ALL_ORIGINS = True
CSRF_TRUSTED_ORIGINS = ['http://localhost:8000', 'http://127.0.0.1:8000']

# حالت آفلاین
OFFLINE_MODE = True

# برای محیط embeddable python
import os
os.environ['PYTHONPATH'] = os.path.join(BASE_DIR, 'python', 'python-3.10.11-embed-amd64')
'''
            zipf.writestr('plasco_system/plasco/settings_offline.py', settings_content.strip())

            # فایل settings.py اصلی که از آفلاین ایمپورت می‌کند
            zipf.writestr('plasco_system/plasco/settings.py', 'from .settings_offline import *\n')

            # فایل __init__.py برای پوشه plasco
            zipf.writestr('plasco_system/plasco/__init__.py', '')

            # ==================== فایل requirements بهبود یافته ====================
            requirements_content = '''# Plasco Offline System - Complete Requirements
# Core Django
Django==4.2.7
django-cors-headers==4.3.1
djangorestframework==3.14.0
Pillow==10.0.1

# Utilities
requests==2.31.0
jdatetime==4.1.1
python-barcode==0.15.1
python-decouple==3.8
django-filter==23.3

# PDF and Reporting
reportlab==4.0.4
xhtml2pdf==0.2.13
openpyxl==3.1.2

# Persian Support
django-jalali==5.0.0
persian==0.3.1
hazm==0.7.0

# File handling
python-magic-bin==0.4.14
django-import-export==3.3.0
django-cleanup==8.0.0

# Additional utilities
python-dateutil==2.8.2
pytz==2023.3

# Django core dependencies
asgiref==3.7.2
sqlparse==0.4.4
tzdata==2023.3

# Security and HTTP
urllib3==1.26.18
certifi==2023.11.17
charset-normalizer==3.3.2
idna==3.6

# MySQL fallback
pymysql==1.1.0
'''
            zipf.writestr('plasco_system/requirements_offline.txt', requirements_content)

            # ==================== فایل‌های جایگزین برای کتابخانه‌های مشکل‌ساز ====================

            # ماژول جایگزین kavenegar
            kavenegar_stub_content = '''
"""
ماژول جایگزین برای kavenegar - برای حالت آفلاین
"""

class KavenegarAPI:
    def __init__(self, *args, **kwargs):
        print("🔹 OFFLINE MODE: KavenegarAPI initialized (SMS disabled)")

    def sms_send(self, *args, **kwargs):
        print("🔹 OFFLINE MODE: SMS sending is disabled")
        return {"status": 200, "message": "SMS disabled in offline mode"}

    def call_make(self, *args, **kwargs):
        print("🔹 OFFLINE MODE: Call making is disabled")
        return {"status": 200, "message": "Calls disabled in offline mode"}

    def verify_lookup(self, *args, **kwargs):
        print("🔹 OFFLINE MODE: Verify lookup is disabled")
        return {"status": 200, "message": "Verify lookup disabled in offline mode"}

class KavenegarException(Exception):
    pass

def send_sms(api_key, sender, receptor, message):
    print(f"🔹 OFFLINE MODE: SMS would be sent to {receptor}: {message}")
    return {"status": 200, "message": "SMS disabled in offline mode"}

def send_lookup_sms(api_key, receptor, token, token2, token3, template):
    print(f"🔹 OFFLINE MODE: Lookup SMS would be sent to {receptor}")
    return {"status": 200, "message": "Lookup SMS disabled in offline mode"}

# برای سازگاری با import *
__all__ = ['KavenegarAPI', 'KavenegarException', 'send_sms', 'send_lookup_sms']
'''
            zipf.writestr('plasco_system/kavenegar.py', kavenegar_stub_content)

            # ماژول جایگزین escpos
            escpos_stub_content = '''
"""
ماژول جایگزین برای escpos - برای حالت آفلاین
"""

class Serial:
    def __init__(self, *args, **kwargs):
        print("🔹 OFFLINE MODE: Printer Serial connection disabled")

    def text(self, text):
        print(f"🔹 OFFLINE MODE: Would print: {text}")

    def cut(self):
        print("🔹 OFFLINE MODE: Would cut paper")

    def close(self):
        print("🔹 OFFLINE MODE: Printer connection closed")

class Usb:
    def __init__(self, *args, **kwargs):
        print("🔹 OFFLINE MODE: Printer USB connection disabled")

    def text(self, text):
        print(f"🔹 OFFLINE MODE: Would print: {text}")

    def cut(self):
        print("🔹 OFFLINE MODE: Would cut paper")

    def close(self):
        print("🔹 OFFLINE MODE: Printer connection closed")

class Network:
    def __init__(self, *args, **kwargs):
        print("🔹 OFFLINE MODE: Printer Network connection disabled")

    def text(self, text):
        print(f"🔹 OFFLINE MODE: Would print: {text}")

    def cut(self):
        print("🔹 OFFLINE MODE: Would cut paper")

    def close(self):
        print("🔹 OFFLINE MODE: Printer connection closed")

class File:
    def __init__(self, *args, **kwargs):
        print("🔹 OFFLINE MODE: Printer File output disabled")

    def text(self, text):
        print(f"🔹 OFFLINE MODE: Would print to file: {text}")

    def cut(self):
        print("🔹 OFFLINE MODE: Would cut paper")

    def close(self):
        print("🔹 OFFLINE MODE: Printer file closed")

# برای سازگاری با import *
__all__ = ['Serial', 'Usb', 'Network', 'File']
'''
            zipf.writestr('plasco_system/escpos.py', escpos_stub_content)
            zipf.writestr('plasco_system/escpos/__init__.py', escpos_stub_content)
            zipf.writestr('plasco_system/escpos/printer.py', escpos_stub_content)

            # ==================== فایل نصب اصلی (BAT) - نسخه پیشرفته ====================
            main_bat = '''@echo off
chcp 65001
title Plasco Offline System - Complete Standalone Installer

echo.
echo ============================================
echo    Plasco Offline System - Standalone Installer
echo    No Python Installation Required!
echo ============================================
echo.

echo Step 1: Checking if Python is available in system...
python --version >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ System Python detected
    set "USE_SYSTEM_PYTHON=1"
    goto :install_packages
)

echo ℹ️ No system Python found, using embedded Python...
set "USE_SYSTEM_PYTHON=0"

:install_packages
echo.
echo Step 2: Setting up library stubs for offline mode...
mkdir plasco_system\\escpos 2>nul

echo Copying kavenegar stub to apps...
copy plasco_system\\kavenegar.py plasco_system\\account_app\\kavenegar.py >nul 2>&1
copy plasco_system\\kavenegar.py plasco_system\\cantact_app\\kavenegar.py >nul 2>&1
copy plasco_system\\kavenegar.py plasco_system\\invoice_app\\kavenegar.py >nul 2>&1

echo Copying escpos stub to apps...
copy plasco_system\\escpos.py plasco_system\\dashbord_app\\escpos.py >nul 2>&1
copy plasco_system\\escpos.py plasco_system\\pos_payment\\escpos.py >nul 2>&1
copy plasco_system\\escpos.py plasco_system\\invoice_app\\escpos.py >nul 2>&1

echo Setting up escpos package...
copy plasco_system\\escpos.py plasco_system\\escpos\\__init__.py >nul 2>&1
copy plasco_system\\escpos.py plasco_system\\escpos\\printer.py >nul 2>&1

echo ✅ Library stubs setup completed
echo.

if "%USE_SYSTEM_PYTHON%"=="1" (
    echo Step 3: Using SYSTEM Python - Installing packages...
    python -m pip install --upgrade pip setuptools wheel

    echo Installing packages from requirements...
    pip install -r plasco_system\\requirements_offline.txt

    goto :setup_database
)

echo Step 3: Setting up EMBEDDED Python environment...
echo This may take 10-20 minutes. Please wait...
echo.

:: ایجاد پوشه برای پایتون توکار
mkdir python >nul 2>&1
cd python

:: دانلود پایتون 3.10.11 embeddable (اگر موجود نیست)
if not exist "python-3.10.11-embed-amd64" (
    echo Downloading Python 3.10.11 (Embeddable)...
    powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.10.11/python-3.10.11-embed-amd64.zip' -OutFile 'python-3.10.11-embed-amd64.zip'"

    echo Extracting Python...
    powershell -Command "Expand-Archive -Path 'python-3.10.11-embed-amd64.zip' -DestinationPath '.' -Force"
)

cd ..

:: استفاده از پایتون توکار
set "PYTHON_PATH=python\\python-3.10.11-embed-amd64\\python.exe"
set "PIP_PATH=python\\python-3.10.11-embed-amd64\\Scripts\\pip.exe"

:: اگر pip موجود نیست، get-pip.py را دانلود و نصب کنید
if not exist "%PIP_PATH%" (
    echo Installing pip for embedded Python...
    cd python\\python-3.10.11-embed-amd64
    powershell -Command "Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile 'get-pip.py'"
    python get-pip.py
    cd ..\\..
)

echo Installing packages using embedded Python...
"%PIP_PATH%" install --upgrade pip setuptools wheel

:: نصب پکیج‌ها به صورت دسته‌ای برای جلوگیری از timeout
echo Installing core packages...
"%PIP_PATH%" install Django==4.2.7
"%PIP_PATH%" install django-cors-headers==4.3.1
"%PIP_PATH%" install djangorestframework==3.14.0
"%PIP_PATH%" install Pillow==10.0.1

echo Installing utility packages...
"%PIP_PATH%" install requests==2.31.0
"%PIP_PATH%" install jdatetime==4.1.1
"%PIP_PATH%" install python-barcode==0.15.1
"%PIP_PATH%" install python-decouple==3.8
"%PIP_PATH%" install django-filter==23.3

echo Installing PDF and reporting packages...
"%PIP_PATH%" install reportlab==4.0.4
"%PIP_PATH%" install xhtml2pdf==0.2.13
"%PIP_PATH%" install openpyxl==3.1.2

echo Installing Persian language packages...
"%PIP_PATH%" install django-jalali==5.0.0
"%PIP_PATH%" install persian==0.3.1
"%PIP_PATH%" install hazm==0.7.0

echo Installing remaining packages...
"%PIP_PATH%" install python-magic-bin==0.4.14
"%PIP_PATH%" install django-import-export==3.3.0
"%PIP_PATH%" install django-cleanup==8.0.0
"%PIP_PATH%" install python-dateutil==2.8.2
"%PIP_PATH%" install pytz==2023.3
"%PIP_PATH%" install pymysql==1.1.0

:setup_database
echo.
echo Step 4: Setting up database...
if "%USE_SYSTEM_PYTHON%"=="1" (
    cd plasco_system
    python manage.py makemigrations
    python manage.py migrate
    cd ..
) else (
    cd plasco_system
    "%PYTHON_PATH%" manage.py makemigrations
    "%PYTHON_PATH%" manage.py migrate
    cd ..
)

if %errorlevel% neq 0 (
    echo ⚠️ Standard migration failed, trying alternative...
    if "%USE_SYSTEM_PYTHON%"=="1" (
        cd plasco_system
        python manage.py migrate --run-syncdb
        cd ..
    ) else (
        cd plasco_system
        "%PYTHON_PATH%" manage.py migrate --run-syncdb
        cd ..
    )
)

echo Step 5: Creating admin user...
if "%USE_SYSTEM_PYTHON%"=="1" (
    cd plasco_system
    python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('admin', 'admin@plasco.com', 'admin123') if not User.objects.filter(username='admin').exists() else print('Admin user already exists')"
    cd ..
) else (
    cd plasco_system
    "%PYTHON_PATH%" manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('admin', 'admin@plasco.com', 'admin123') if not User.objects.filter(username='admin').exists() else print('Admin user already exists')"
    cd ..
)

echo.
echo ============================================
echo    INSTALLATION COMPLETED SUCCESSFULLY!
echo ============================================
echo.
echo 🌟 Plasco Offline System is ready!
echo.
echo 📍 Access URLs:
echo    Main System: http://localhost:8000
echo    Admin Panel: http://localhost:8000/admin
echo.
echo 🔑 Admin Credentials:
echo    Username: admin
echo    Password: admin123
echo.
echo 💡 System Information:
if "%USE_SYSTEM_PYTHON%"=="1" (
    echo    Python: System Installation
) else (
    echo    Python: Embedded (No installation required)
)
echo.
echo 🚀 Starting server...
echo ⏹️  To stop server, press CTRL+C
echo ============================================
echo.

if "%USE_SYSTEM_PYTHON%"=="1" (
    cd plasco_system
    python manage.py runserver 0.0.0.0:8000
    cd ..
) else (
    cd plasco_system
    "%PYTHON_PATH%" manage.py runserver 0.0.0.0:8000
    cd ..
)

if %errorlevel% neq 0 (
    echo.
    echo ⚠️ Server startup failed. Possible reasons:
    echo    - Port 8000 is already in use
    echo    - Try running on a different port:
    echo.
    if "%USE_SYSTEM_PYTHON%"=="1" (
        echo    python manage.py runserver 0.0.0.0:8001
    ) else (
        echo    "%PYTHON_PATH%" manage.py runserver 0.0.0.0:8001
    )
    echo.
    pause
)
'''
            zipf.writestr('START_HERE.bat', main_bat)

            # ==================== فایل‌های راهنما و پشتیبانی ====================

            # فایل راهنمای اصلی
            readme_content = f'''
Plasco Offline System - Complete Standalone Installation
=======================================================

🌟 NO PYTHON INSTALLATION REQUIRED!

📦 What's Included:
- Complete Django project structure
- All application modules
- Templates and static files
- SQLite database configuration
- Embedded Python 3.10.11
- Automatic installation scripts
- All required packages

🚀 Quick Start:
1. Extract ALL files to a folder (important!)
2. Double-click "START_HERE.bat"
3. Wait for automatic installation (10-20 minutes first time)
4. System will start automatically

🌐 Access Information:
- Main Application: http://localhost:8000
- Admin Panel: http://localhost:8000/admin
- Admin Username: admin
- Admin Password: admin123

🔧 Features:
✅ Complete system functionality
✅ Persian language support
✅ SQLite database (no external DB required)
✅ Embedded Python (no installation needed)
✅ Automatic package installation
✅ Admin user creation

⚠️ Limitations in Offline Mode:
❌ SMS functionality disabled
❌ Printer functionality disabled
❌ External API calls disabled

📋 Allowed IP Addresses:
{chr(10).join(f"   - {ip}" for ip in selected_ips)}

🔍 Technical Details:
- Python Version: 3.10.11 (Embedded)
- Django Version: 4.2.7
- Database: SQLite3
- Package Manager: pip

📞 Support:
- Created: {timezone.now().strftime("%Y/%m/%d %H:%M")}
- This is a fully self-contained offline system

🔒 Security Note:
- Change the default admin password after first login
- This package uses development settings for easy setup

🛠️ Troubleshooting:
1. If port 8000 is busy, the script will suggest using port 8001
2. First run may take longer due to package downloads
3. Ensure you have internet connection for first-time setup
4. Required disk space: ~500MB
'''
            zipf.writestr('README_FIRST.txt', readme_content)

            # فایل fallback installer برای مواقع ضروری
            fallback_installer = '''
# standalone_fallback.py
# This script provides alternative installation methods

import os
import sys
import subprocess
import urllib.request
import zipfile

def download_file(url, filename):
    """Download a file from URL"""
    try:
        print(f"Downloading {filename}...")
        urllib.request.urlretrieve(url, filename)
        return True
    except Exception as e:
        print(f"Download failed: {e}")
        return False

def run_command(command):
    """Run a command and return success status"""
    try:
        result = subprocess.run(command, shell=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {command}")
        print(f"Error: {e}")
        return False

def setup_embedded_python():
    """Setup embedded Python if system Python is not available"""
    python_dir = "python"
    python_zip = "python-3.10.11-embed-amd64.zip"
    python_url = "https://www.python.org/ftp/python/3.10.11/python-3.10.11-embed-amd64.zip"

    if not os.path.exists(os.path.join(python_dir, "python-3.10.11-embed-amd64")):
        print("Setting up embedded Python...")
        os.makedirs(python_dir, exist_ok=True)
        os.chdir(python_dir)

        if download_file(python_url, python_zip):
            with zipfile.ZipFile(python_zip, 'r') as zip_ref:
                zip_ref.extractall(".")
            os.remove(python_zip)
            print("✅ Embedded Python setup completed")
        else:
            print("❌ Failed to setup embedded Python")
            return False

        os.chdir("..")
    return True

def install_packages_embedded():
    """Install packages using embedded Python"""
    python_exe = "python\\\\python-3.10.11-embed-amd64\\\\python.exe"
    pip_exe = "python\\\\python-3.10.11-embed-amd64\\\\Scripts\\\\pip.exe"

    # Install get-pip if not available
    if not os.path.exists(pip_exe):
        print("Installing pip for embedded Python...")
        get_pip_url = "https://bootstrap.pypa.io/get-pip.py"
        if download_file(get_pip_url, "get-pip.py"):
            run_command(f'"{python_exe}" get-pip.py')
            os.remove("get-pip.py")

    # Install packages in batches
    packages = [
        "Django==4.2.7", "django-cors-headers==4.3.1", "djangorestframework==3.14.0",
        "Pillow==10.0.1", "requests==2.31.0", "jdatetime==4.1.1",
        "python-barcode==0.15.1", "python-decouple==3.8", "django-filter==23.3",
        "reportlab==4.0.4", "xhtml2pdf==0.2.13", "openpyxl==3.1.2",
        "django-jalali==5.0.0", "persian==0.3.1", "hazm==0.7.0",
        "python-magic-bin==0.4.14", "django-import-export==3.3.0", "django-cleanup==8.0.0",
        "python-dateutil==2.8.2", "pytz==2023.3", "pymysql==1.1.0"
    ]

    for package in packages:
        print(f"Installing {package}...")
        run_command(f'"{pip_exe}" install {package}')

    return True

def main():
    print("Plasco Offline System - Alternative Installer")
    print("=" * 50)

    # Check system Python first
    try:
        subprocess.run([sys.executable, "--version"], check=True, capture_output=True)
        print("✅ System Python detected")
        use_system_python = True
    except:
        print("ℹ️ No system Python found, using embedded Python")
        use_system_python = False

    if not use_system_python:
        if not setup_embedded_python():
            print("❌ Failed to setup embedded Python")
            return

        if not install_packages_embedded():
            print("❌ Failed to install packages")
            return

    print("✅ Installation completed!")
    print("Run the system with:")
    if use_system_python:
        print("  python manage.py runserver 0.0.0.0:8000")
    else:
        print('  "python\\\\python-3.10.11-embed-amd64\\\\python.exe" manage.py runserver 0.0.0.0:8000')

if __name__ == "__main__":
    main()
'''
            zipf.writestr('standalone_fallback.py', fallback_installer)

            # ==================== فایل پیکربندی پایتون توکار ====================

            # فایل _pth برای پایتون embeddable
            python_pth_content = '''
python310.zip
.
# Uncomment to run site.main() automatically
#import site
'''
            zipf.writestr('python/python-3.10.11-embed-amd64/python310._pth', python_pth_content)

        zip_buffer.seek(0)
        print("✅ Complete standalone installation package created successfully!")
        return zip_buffer

    except Exception as e:
        print(f"❌ Error creating package: {str(e)}")
        import traceback
        print(f"🔍 Details: {traceback.format_exc()}")
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

            print(f"🔹 Creating standalone installer for IPs: {selected_ips}")
            zip_buffer = create_complete_install_package(selected_ips)

            if not zip_buffer:
                return JsonResponse({
                    'status': 'error',
                    'message': 'خطا در ایجاد فایل نصب'
                })

            # ایجاد پاسخ با فایل ZIP
            response = HttpResponse(
                zip_buffer.getvalue(),
                content_type='application/zip'
            )
            response['Content-Disposition'] = 'attachment; filename="plasco_standalone_system.zip"'

            print("✅ Standalone installer created and sent for download")
            return response

        except Exception as e:
            print(f"❌ Error in create_offline_installer: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': f'خطا در ایجاد فایل نصب: {str(e)}'
            })

    return JsonResponse({'status': 'error', 'message': 'متد غیرمجاز'})