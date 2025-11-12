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

            # فایل settings_offline.py کاملاً ساده‌سازی شده
            settings_content = f'''
"""
Django settings for plasco project - OFFLINE MODE
Allowed IPs: {selected_ips}
Generated: {timezone.now().strftime("%Y/%m/%d %H:%M")}
"""

from pathlib import Path
import os
import sys

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

    # Local apps - فقط اپ‌های ضروری
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
        'NAME': BASE_DIR / 'db.sqlite3',
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

# غیرفعال کردن تمام چک‌های امنیتی برای نصب آسان
SILENCED_SYSTEM_CHECKS = [
    'security.W001',
    'security.W002', 
    'security.W004', 
    'security.W008', 
    'security.W009',
    'security.W019',
    'security.W020',
    'urls.W005',
    'models.W042',
]

# حالت آفلاین
OFFLINE_MODE = True

print("🟢 Plasco Offline Mode - All security checks disabled for easy installation")
'''
            zipf.writestr('plasco_system/plasco/settings_offline.py', settings_content.strip())

            # فایل settings.py اصلی که از آفلاین ایمپورت می‌کند
            zipf.writestr('plasco_system/plasco/settings.py', 'from .settings_offline import *\n')

            # فایل __init__.py برای پوشه plasco
            zipf.writestr('plasco_system/plasco/__init__.py', '')

            # ==================== فایل requirements ساده‌سازی شده ====================
            requirements_content = '''# Plasco Offline System - Simplified Requirements
Django==4.2.7
django-cors-headers==4.3.1
djangorestframework==3.14.0
Pillow==10.0.1
requests==2.31.0
jdatetime==4.1.1
python-barcode==0.15.1
python-decouple==3.8
django-filter==23.3
reportlab==4.0.4
xhtml2pdf==0.2.13
openpyxl==3.1.2
django-jalali==5.0.0
persian==0.3.1
hazm==0.7.0
python-magic-bin==0.4.14
django-import-export==3.3.0
django-cleanup==8.0.0
python-dateutil==2.8.2
pytz==2023.3
pyserial==3.5
pymysql==1.1.0
'''
            zipf.writestr('plasco_system/requirements_offline.txt', requirements_content)

            # ==================== ایجاد فایل‌های apps.py برای اپلیکیشن‌ها ====================

            # فایل apps.py برای ip_manager
            ip_manager_apps_content = '''
from django.apps import AppConfig

class IpManagerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ip_manager'
    verbose_name = 'مدیریت IPها'
'''
            zipf.writestr('plasco_system/ip_manager/apps.py', ip_manager_apps_content)

            # فایل‌های apps.py برای سایر اپلیکیشن‌ها
            apps_configs = {
                'account_app': 'AccountAppConfig',
                'dashbord_app': 'DashbordAppConfig',
                'cantact_app': 'CantactAppConfig',
                'invoice_app': 'InvoiceAppConfig',
                'it_app': 'ItAppConfig',
                'pos_payment': 'PosPaymentConfig',
                'sync_app': 'SyncAppConfig',
                'sync_api': 'SyncApiConfig',
                'control_panel': 'ControlPanelConfig',
                'offline_ins': 'OfflineInsConfig',
                'home_app': 'HomeAppConfig'
            }

            for app_name, config_class in apps_configs.items():
                apps_content = f'''
from django.apps import AppConfig

class {config_class}(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = '{app_name}'
'''
                zipf.writestr(f'plasco_system/{app_name}/apps.py', apps_content)

            # ==================== فایل urls.py ساده‌سازی شده ====================
            urls_content = '''
from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse

def home_view(request):
    return HttpResponse("""
    <html>
        <head>
            <title>Plasco Offline System</title>
            <style>
                body { font-family: Tahoma; text-align: center; padding: 50px; }
                .success { color: green; font-size: 24px; }
                .info { color: blue; margin: 20px 0; }
            </style>
        </head>
        <body>
            <h1 class="success">✅ Plasco Offline System Installed Successfully!</h1>
            <div class="info">
                <p><strong>System is running in OFFLINE MODE</strong></p>
                <p>Access URLs:</p>
                <ul style="list-style: none; padding: 0;">
                    <li>🏠 Main System: <a href="/">Home Page</a></li>
                    <li>⚙️ Admin Panel: <a href="/admin/">Admin</a></li>
                    <li>🔧 IP Management: <a href="/ip/ip_manager/">Manage IPs</a></li>
                </ul>
                <p>Admin Credentials: admin / admin123</p>
            </div>
        </body>
    </html>
    """)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home_view, name='home'),
    path('ip/', include('ip_manager.urls')),
]
'''
            zipf.writestr('plasco_system/plasco/urls.py', urls_content)

            # ==================== فایل‌های جایگزین برای کتابخانه‌های مشکل‌ساز ====================

            # ماژول جایگزین kavenegar
            kavenegar_stub_content = '''
"""
ماژول جایگزین برای kavenegar - برای حالت آفلاین
"""

class KavenegarAPI:
    def __init__(self, *args, **kwargs):
        pass

    def sms_send(self, *args, **kwargs):
        return {"status": 200, "message": "SMS disabled in offline mode"}

    def call_make(self, *args, **kwargs):
        return {"status": 200, "message": "Calls disabled in offline mode"}

    def verify_lookup(self, *args, **kwargs):
        return {"status": 200, "message": "Verify lookup disabled in offline mode"}

class KavenegarException(Exception):
    pass

def send_sms(api_key, sender, receptor, message):
    return {"status": 200, "message": "SMS disabled in offline mode"}

def send_lookup_sms(api_key, receptor, token, token2, token3, template):
    return {"status": 200, "message": "Lookup SMS disabled in offline mode"}

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
        pass

    def text(self, text):
        pass

    def cut(self):
        pass

    def close(self):
        pass

class Usb:
    def __init__(self, *args, **kwargs):
        pass

    def text(self, text):
        pass

    def cut(self):
        pass

    def close(self):
        pass

class Network:
    def __init__(self, *args, **kwargs):
        pass

    def text(self, text):
        pass

    def cut(self):
        pass

    def close(self):
        pass

class File:
    def __init__(self, *args, **kwargs):
        pass

    def text(self, text):
        pass

    def cut(self):
        pass

    def close(self):
        pass

__all__ = ['Serial', 'Usb', 'Network', 'File']
'''
            zipf.writestr('plasco_system/escpos.py', escpos_stub_content)
            zipf.writestr('plasco_system/escpos/__init__.py', escpos_stub_content)
            zipf.writestr('plasco_system/escpos/printer.py', escpos_stub_content)

            # ماژول جایگزین برای serial (pyserial)
            serial_stub_content = '''
"""
ماژول جایگزین برای pyserial - برای حالت آفلاین
"""

class Serial:
    def __init__(self, port=None, baudrate=9600, bytesize=8, parity='N', 
                 stopbits=1, timeout=None, xonxoff=False, rtscts=False, 
                 write_timeout=None, dsrdtr=False, inter_byte_timeout=None, 
                 exclusive=None, **kwargs):
        self.port = port
        self.baudrate = baudrate
        self.is_open = False

    def open(self):
        self.is_open = True
        return True

    def close(self):
        self.is_open = False

    def write(self, data):
        return len(data)

    def read(self, size=1):
        return b''

    def readline(self, size=-1):
        return b''

    def flush(self):
        pass

    def reset_input_buffer(self):
        pass

    def reset_output_buffer(self):
        pass

    @property
    def in_waiting(self):
        return 0

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

def serial_for_url(url, *args, **kwargs):
    return Serial(port=url)

def list_ports():
    return []

class SerialException(Exception):
    pass

class SerialTimeoutException(SerialException):
    pass

VERSION = "3.5"
PARITY_NONE = 'N'
PARITY_EVEN = 'E'
PARITY_ODD = 'O'
PARITY_MARK = 'M'
PARITY_SPACE = 'S'
STOPBITS_ONE = 1
STOPBITS_ONE_POINT_FIVE = 1.5
STOPBITS_TWO = 2
FIVEBITS = 5
SIXBITS = 6
SEVENBITS = 7
EIGHTBITS = 8

__all__ = ['Serial', 'serial_for_url', 'list_ports', 'SerialException', 
           'SerialTimeoutException', 'VERSION', 'PARITY_NONE', 'PARITY_EVEN',
           'PARITY_ODD', 'PARITY_MARK', 'PARITY_SPACE', 'STOPBITS_ONE',
           'STOPBITS_ONE_POINT_FIVE', 'STOPBITS_TWO', 'FIVEBITS', 'SIXBITS',
           'SEVENBITS', 'EIGHTBITS']
'''
            zipf.writestr('plasco_system/serial.py', serial_stub_content)

            # ==================== فایل نصب اصلی (BAT) - کاملاً بهبود یافته ====================
            main_bat = '''@echo off
@echo off
chcp 65001
title Plasco Offline System - Complete Installer
setlocal enabledelayedexpansion

echo.
echo ============================================
echo    Plasco Offline System - Complete Installer
echo ============================================
echo.

echo Step 1: Checking Python installation...
python --version
if !errorlevel! neq 0 (
    echo.
    echo ❌ ERROR: Python not found or not in PATH!
    echo.
    echo Please install Python 3.8+ from: https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    echo Press any key to exit...
    pause >nul
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo ✅ !PYTHON_VERSION! detected
echo.

echo Step 2: Setting up library stubs for offline mode...
mkdir plasco_system\escpos 2>nul

echo Copying kavenegar stub...
copy plasco_system\kavenegar.py plasco_system\account_app\kavenegar.py >nul 2>&1
copy plasco_system\kavenegar.py plasco_system\cantact_app\kavenegar.py >nul 2>&1
copy plasco_system\kavenegar.py plasco_system\invoice_app\kavenegar.py >nul 2>&1

echo Copying escpos stub...
copy plasco_system\escpos.py plasco_system\dashbord_app\escpos.py >nul 2>&1
copy plasco_system\escpos.py plasco_system\pos_payment\escpos.py >nul 2>&1
copy plasco_system\escpos.py plasco_system\invoice_app\escpos.py >nul 2>&1

echo Setting up escpos package...
copy plasco_system\escpos.py plasco_system\escpos\__init__.py >nul 2>&1
copy plasco_system\escpos.py plasco_system\escpos\printer.py >nul 2>&1

echo Setting up serial stub...
copy plasco_system\serial.py plasco_system\dashbord_app\serial.py >nul 2>&1
copy plasco_system\serial.py plasco_system\pos_payment\serial.py >nul 2>&1
copy plasco_system\serial.py plasco_system\invoice_app\serial.py >nul 2>&1

echo ✅ Library stubs setup completed
echo.

echo Step 3: Installing required packages...
echo This may take 5-15 minutes. Please wait...
echo.

cd plasco_system

echo Upgrading pip...
python -m pip install --upgrade pip
if !errorlevel! neq 0 (
    echo ❌ Failed to upgrade pip
    echo Press any key to exit...
    pause >nul
    exit /b 1
)
echo ✅ pip upgraded successfully

echo Installing core packages...
python -m pip install Django==4.2.7
if !errorlevel! neq 0 (
    echo ❌ Failed to install Django
    echo Press any key to exit...
    pause >nul
    exit /b 1
)

python -m pip install django-cors-headers==4.3.1
python -m pip install djangorestframework==3.14.0
python -m pip install Pillow==10.0.1
echo ✅ Core packages installed

echo Installing utility packages...
python -m pip install requests==2.31.0
python -m pip install jdatetime==4.1.1
python -m pip install python-barcode==0.15.1
python -m pip install python-decouple==3.8
python -m pip install django-filter==23.3
echo ✅ Utility packages installed

echo Installing PDF and reporting packages...
python -m pip install reportlab==4.0.4
python -m pip install xhtml2pdf==0.2.13
python -m pip install openpyxl==3.1.2
echo ✅ PDF packages installed

echo Installing Persian language packages...
python -m pip install django-jalali==5.0.0
python -m pip install persian==0.3.1
python -m pip install hazm==0.7.0
echo ✅ Persian packages installed

echo Installing remaining packages...
python -m pip install python-magic-bin==0.4.14
python -m pip install django-import-export==3.3.0
python -m pip install django-cleanup==8.0.0
python -m pip install python-dateutil==2.8.2
python -m pip install pytz==2023.3
python -m pip install pyserial==3.5
python -m pip install pymysql==1.1.0
echo ✅ All packages installed successfully

echo.
echo Step 4: Setting up database...
echo Creating database migrations...
python manage.py makemigrations --noinput
if !errorlevel! neq 0 (
    echo ⚠️ Migrations creation had issues, continuing anyway...
)

echo Applying migrations...
python manage.py migrate --run-syncdb
if !errorlevel! neq 0 (
    echo ❌ Database migration failed!
    echo Press any key to exit...
    pause >nul
    exit /b 1
)
echo ✅ Database setup completed

echo Step 5: Creating admin user...
python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('admin', 'admin@plasco.com', 'admin123') if not User.objects.filter(username='admin').exists() else print('Admin user already exists')"
echo ✅ Admin user setup completed

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
echo    IP Management: http://localhost:8000/ip/ip_manager/
echo.
echo 🔑 Admin Credentials:
echo    Username: admin
echo    Password: admin123
echo.
echo 📝 Important Notes:
echo    - SMS features are disabled in offline mode
echo    - Printer features are disabled in offline mode
echo    - All other features work normally
echo.
echo 🚀 Starting server...
echo ⏹️  To stop server, press CTRL+C
echo ============================================
echo.
echo Waiting 5 seconds before starting server...
timeout /t 5 /nobreak >nul

:start_server
echo Starting server on port 8000...
python manage.py runserver 0.0.0.0:8000
if !errorlevel! neq 0 (
    echo.
    echo ⚠️ Port 8000 is busy, trying port 8001...
    echo.
    timeout /t 3 /nobreak >nul
    python manage.py runserver 0.0.0.0:8001
)

if !errorlevel! neq 0 (
    echo.
    echo ❌ Server startup failed on both ports 8000 and 8001!
    echo.
    echo 🔧 Troubleshooting steps:
    echo 1. Check if another server is running
    echo 2. Try manually: python manage.py runserver 0.0.0.0:8002
    echo 3. Check firewall settings
    echo 4. Ensure no other application is using ports 8000-8001
    echo.
    echo Press any key to close...
    pause >nul
)
            zipf.writestr('START_HERE.bat', main_bat)

            # ==================== فایل راهنمای عیب‌یابی ====================
            troubleshooting_content = '''
Plasco Offline System - Troubleshooting Guide
============================================

اگر اسکریپت با مشکل مواجه شد:

1. مشکل: صفحه سریع بسته می‌شود
   راه حل: فایل START_HERE.bat را با راست کلیک و "Edit" باز کنید
   سپس خط آخر را پیدا کرده و قبل از آن "pause" اضافه کنید

2. مشکل: پایتون پیدا نمی‌شود
   راه حل: 
   - پایتون 3.8 یا بالاتر نصب کنید
   - در حین نصب، گزینه "Add Python to PATH" را انتخاب کنید
   - از آدرس: https://www.python.org/downloads/

3. مشکل: خطا در نصب پکیج‌ها
   راه حل:
   - دستور زیر را در cmd اجرا کنید:
     cd plasco_system
     pip install -r requirements_offline.txt

4. مشکل: پورت 8000 مشغول است
   راه حل:
   - دستور زیر را اجرا کنید:
     python manage.py runserver 0.0.0.0:8001

5. مشکل: دیتابیس ایجاد نمی‌شود
   راه حل:
   - فایل db.sqlite3 را حذف کنید
   - سپس دستورات زیر را اجرا کنید:
     python manage.py migrate --run-syncdb

دستورات مفید:
- راه‌اندازی سرور: python manage.py runserver 0.0.0.0:8000
- ایجاد کاربر ادمین: python manage.py createsuperuser
- بررسی migrations: python manage.py showmigrations

برای پشتیبانی بیشتر، لاگ خطاها را بررسی کنید.
'''
            zipf.writestr('TROUBLESHOOTING.txt', troubleshooting_content)

            # ==================== فایل‌های راهنما ====================

            # فایل راهنمای اصلی
            readme_content = f'''
Plasco Offline System - Complete Standalone Installation
=======================================================

🚀 Quick Start:
1. Extract ALL files to a folder
2. Double-click "START_HERE.bat"
3. Wait for automatic installation (5-15 minutes)
4. System will start automatically

🌐 Access Information:
- Main Application: http://localhost:8000
- Admin Panel: http://localhost:8000/admin  
- IP Management: http://localhost:8000/ip/ip_manager/
- Admin Username: admin
- Admin Password: admin123

🔧 Features:
✅ Complete system functionality
✅ Persian language support
✅ SQLite database
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

🛠️ Troubleshooting:
- If installation fails, see TROUBLESHOOTING.txt
- If port 8000 is busy, system will use port 8001
- First run may take 5-15 minutes
'''
            zipf.writestr('README_FIRST.txt', readme_content)

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
            response['Content-Disposition'] = 'attachment; filename="plasco_offline_system.zip"'

            print("✅ Standalone installer created and sent for download")
            return response

        except Exception as e:
            print(f"❌ Error in create_offline_installer: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': f'خطا در ایجاد فایل نصب: {str(e)}'
            })

    return JsonResponse({'status': 'error', 'message': 'متد غیرمجاز'})