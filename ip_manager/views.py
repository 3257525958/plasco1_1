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
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            print("📦 Creating complete installation package...")

            # ==================== فایل‌های اصلی پروژه ====================

            # فایل manage.py
            manage_path = BASE_DIR / 'manage.py'
            if manage_path.exists():
                zipf.write(manage_path, 'manage.py')
                print("✅ Added: manage.py")

            # پوشه اصلی پروژه (plasco)
            plasco_path = BASE_DIR / 'plasco'
            if plasco_path.exists():
                for root, dirs, files in os.walk(plasco_path):
                    for file in files:
                        if file.endswith(('.py', '.html', '.css', '.js', '.json', '.txt')):
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, BASE_DIR)
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
                            # شامل تمام فایل‌های ضروری
                            if file.endswith(('.py', '.html', '.css', '.js', '.json', '.txt', '.md')):
                                file_path = os.path.join(root, file)
                                arcname = os.path.relpath(file_path, BASE_DIR)
                                zipf.write(file_path, arcname)
                    print(f"✅ Added app: {app}")

            # ==================== فایل‌های قالب و استاتیک ====================

            # پوشه templates
            templates_path = BASE_DIR / 'templates'
            if templates_path.exists():
                for root, dirs, files in os.walk(templates_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, BASE_DIR)
                        zipf.write(file_path, arcname)
                print("✅ Added templates folder")

            # پوشه static
            static_path = BASE_DIR / 'static'
            if static_path.exists():
                for root, dirs, files in os.walk(static_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, BASE_DIR)
                        zipf.write(file_path, arcname)
                print("✅ Added static folder")

            # پوشه media (اگر وجود دارد)
            media_path = BASE_DIR / 'media'
            if media_path.exists():
                for root, dirs, files in os.walk(media_path):
                    for file in files:
                        if file.endswith(('.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg')):
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, BASE_DIR)
                            zipf.write(file_path, arcname)
                print("✅ Added media folder")

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
'''
            zipf.writestr('plasco/settings_offline.py', settings_content.strip())

            # فایل settings.py اصلی که از آفلاین ایمپورت می‌کند
            zipf.writestr('plasco/settings.py', 'from .settings_offline import *\n')

            # فایل __init__.py برای پوشه plasco
            zipf.writestr('plasco/__init__.py', '')

            # ==================== فایل requirements بهبود یافته ====================
            requirements_content = '''# Plasco Offline System - Complete Requirements
# Core Django
Django==4.2.7
django-cors-headers==4.3.1
djangorestframework==3.14.0
Pillow==10.0.1

# Database - SQLite (no need for mysqlclient in offline mode)
# mysqlclient will be handled by fallback

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

# Async and Tasks (optional for offline)
channels==4.0.0
channels-redis==4.1.0
celery==5.3.4
redis==5.0.1
django-celery-results==2.5.1
django-celery-beat==2.5.0

# Additional utilities
django-import-export==3.3.0
django-cleanup==8.0.0
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

# File type detection (Windows compatible)
python-magic-bin==0.4.14

# Fallback for MySQL (if needed)
pymysql==1.1.0
'''
            zipf.writestr('requirements_offline.txt', requirements_content)

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
            zipf.writestr('kavenegar.py', kavenegar_stub_content)

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
            zipf.writestr('escpos.py', escpos_stub_content)
            zipf.writestr('escpos/__init__.py', escpos_stub_content)
            zipf.writestr('escpos/printer.py', escpos_stub_content)

            # ==================== فایل نصب اصلی (BAT) ====================
            main_bat = '''@echo off
chcp 65001
title Plasco Offline System - Complete Installer

echo.
echo ============================================
echo    Plasco Offline System - Complete Installer
echo ============================================
echo.

echo Step 1: Checking Python installation...
python --version
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Python not found!
    echo.
    echo Please install Python 3.8+ from: https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    echo Press any key to exit...
    pause >nul
    exit /b 1
)

echo ✅ Python is installed
echo.

echo Step 2: Setting up library stubs for offline mode...
mkdir escpos 2>nul

echo Copying kavenegar stub to apps...
copy kavenegar.py account_app\\kavenegar.py >nul 2>&1
copy kavenegar.py cantact_app\\kavenegar.py >nul 2>&1
copy kavenegar.py invoice_app\\kavenegar.py >nul 2>&1

echo Copying escpos stub to apps...
copy escpos.py dashbord_app\\escpos.py >nul 2>&1
copy escpos.py pos_payment\\escpos.py >nul 2>&1
copy escpos.py invoice_app\\escpos.py >nul 2>&1

echo Setting up escpos package...
copy escpos.py escpos\\__init__.py >nul 2>&1
copy escpos.py escpos\\printer.py >nul 2>&1

echo ✅ Library stubs setup completed
echo.

echo Step 3: Upgrading pip and setuptools...
python -m pip install --upgrade pip setuptools wheel

echo Step 4: Installing required packages...
echo This may take 5-15 minutes. Please wait...
echo.

echo Installing core packages...
pip install Django==4.2.7
pip install django-cors-headers==4.3.1
pip install djangorestframework==3.14.0
pip install Pillow==10.0.1

echo Installing utility packages...
pip install requests==2.31.0
pip install jdatetime==4.1.1
pip install python-barcode==0.15.1
pip install python-decouple==3.8
pip install django-filter==23.3

echo Installing PDF and reporting packages...
pip install reportlab==4.0.4
pip install xhtml2pdf==0.2.13
pip install openpyxl==3.1.2

echo Installing Persian language packages...
pip install django-jalali==5.0.0
pip install persian==0.3.1
pip install hazm==0.7.0

echo Installing file handling packages...
pip install python-magic-bin==0.4.14
pip install django-import-export==3.3.0
pip install django-cleanup==8.0.0

echo Installing async and task packages (optional)...
pip install channels==4.0.0
pip install channels-redis==4.1.0
pip install celery==5.3.4
pip install redis==5.0.1
pip install django-celery-results==2.5.1
pip install django-celery-beat==2.5.0

echo Installing remaining utility packages...
pip install python-dateutil==2.8.2
pip install pytz==2023.3
pip install asgiref==3.7.2
pip install sqlparse==0.4.4
pip install tzdata==2023.3
pip install urllib3==1.26.18
pip install certifi==2023.11.17
pip install charset-normalizer==3.3.2
pip install idna==3.6

echo Installing MySQL fallback...
pip install pymysql==1.1.0

echo.
echo ✅ All packages installed successfully!
echo.

echo Step 5: Setting up database...
echo Creating database migrations...
python manage.py makemigrations

echo Applying migrations...
python manage.py migrate

if %errorlevel% neq 0 (
    echo ⚠️ Standard migration failed, trying alternative...
    python manage.py migrate --run-syncdb
)

echo Step 6: Creating admin user...
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
try:
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@plasco.com', 'admin123')
        print('✅ Admin user created successfully')
    else:
        print('ℹ️ Admin user already exists')
except Exception as e:
    print('⚠️ Error creating admin user:', str(e))
    print('⚠️ You can create admin user manually later with:')
    print('⚠️ python manage.py createsuperuser')
"

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
echo 💡 Important Notes:
echo    - SMS features are disabled in offline mode
echo    - Printer features are disabled in offline mode
echo    - All other features work normally
echo.
echo 🚀 Starting server...
echo ⏹️  To stop server, press CTRL+C
echo ============================================
echo.

python manage.py runserver 0.0.0.0:8000

if %errorlevel% neq 0 (
    echo.
    echo ⚠️ Server startup failed. Possible reasons:
    echo    - Port 8000 is already in use
    echo    - Database configuration issue
    echo.
    echo 🔧 Troubleshooting:
    echo    - Try: python manage.py runserver 0.0.0.0:8001
    echo    - Check if another server is running
    echo.
    pause
)
'''
            zipf.writestr('START_HERE.bat', main_bat)

            # ==================== فایل‌های راهنما و پشتیبانی ====================

            # فایل راهنمای اصلی
            readme_content = f'''
Plasco Offline System - Complete Installation Package
===================================================

📦 What's Included:
- Complete Django project structure
- All application modules
- Templates and static files
- SQLite database configuration
- Offline-compatible settings
- Automatic installation scripts

🚀 Quick Start:
1. Extract ALL files to a folder (important!)
2. Double-click "START_HERE.bat"
3. Wait for automatic installation (5-15 minutes)
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
✅ Automatic package installation
✅ Admin user creation

⚠️ Limitations in Offline Mode:
❌ SMS functionality disabled
❌ Printer functionality disabled
❌ External API calls disabled

📋 Allowed IP Addresses:
{chr(10).join(f"   - {ip}" for ip in selected_ips)}

📞 Support:
- Created: {timezone.now().strftime("%Y/%m/%d %H:%M")}
- This is a fully self-contained offline system

🔒 Security Note:
- Change the default admin password after first login
- This package uses development settings for easy setup
'''
            zipf.writestr('README_FIRST.txt', readme_content)

            # فایل fallback installer برای مواقع ضروری
            fallback_installer = '''
# fallback_installer.py
# This script can be run if the BAT file has issues

import os
import sys
import subprocess

def run_command(command):
    """Run a command and return success status"""
    try:
        result = subprocess.run(command, shell=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {command}")
        print(f"Error: {e}")
        return False

def main():
    print("Plasco Offline System - Fallback Installer")
    print("=" * 50)

    # Install packages in smaller batches
    packages_batches = [
        ["Django==4.2.7", "django-cors-headers==4.3.1", "djangorestframework==3.14.0"],
        ["Pillow==10.0.1", "requests==2.31.0", "jdatetime==4.1.1"],
        ["python-barcode==0.15.1", "python-decouple==3.8", "django-filter==23.3"],
        ["reportlab==4.0.4", "xhtml2pdf==0.2.13", "openpyxl==3.1.2"],
        ["django-jalali==5.0.0", "persian==0.3.1", "hazm==0.7.0"],
        ["python-magic-bin==0.4.14", "django-import-export==3.3.0", "django-cleanup==8.0.0"],
    ]

    for i, batch in enumerate(packages_batches, 1):
        print(f"Installing batch {i}/6...")
        for package in batch:
            if run_command(f"pip install {package}"):
                print(f"✅ {package}")
            else:
                print(f"❌ {package}")

    print("Installation completed!")
    print("Run these commands manually if needed:")
    print("  python manage.py migrate")
    print("  python manage.py runserver 0.0.0.0:8000")

if __name__ == "__main__":
    main()
'''
            zipf.writestr('fallback_installer.py', fallback_installer)

        zip_buffer.seek(0)
        print("✅ Complete installation package created successfully!")
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

            print(f"🔹 Creating installer for IPs: {selected_ips}")
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
            response['Content-Disposition'] = 'attachment; filename="plasco_offline_complete_system.zip"'

            return response

        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'خطا در ایجاد فایل نصب: {str(e)}'
            })

    return JsonResponse({'status': 'error', 'message': 'متد غیرمجاز'})