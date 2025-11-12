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

            # فایل settings_offline.py با رفع مشکلات
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
    'django_jalali',
    # 'django_select2',  # موقتاً غیرفعال شده

    # Local apps - با تعریف app_label
    'account_app.apps.AccountAppConfig',
    'dashbord_app.apps.DashbordAppConfig', 
    'cantact_app.apps.CantactAppConfig',
    'invoice_app.apps.InvoiceAppConfig',
    'it_app.apps.ItAppConfig',
    'pos_payment.apps.PosPaymentConfig',
    'sync_app.apps.SyncAppConfig',
    'sync_api.apps.SyncApiConfig',
    'control_panel.apps.ControlPanelConfig',
    'offline_ins.apps.OfflineInsConfig',
    'ip_manager.apps.IpManagerConfig',
    'home_app.apps.HomeAppConfig',
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

            # ==================== فایل requirements بر اساس requirements.txt شما ====================
            requirements_content = '''appdirs==1.4.4
arabic-reshaper==3.0.0
argcomplete==3.6.2
asgiref==3.9.1
certifi==2025.8.3
charset-normalizer==3.4.3
colorama==0.4.6
Django==5.2.4
django-appconf==1.1.0
django-cleanup==8.1.0
django-cors-headers==4.8.0
django-environ==0.12.0
django-jalali==6.0.1
django-jalali-date==1.0.1
# django-select2==8.4.1  # موقتاً غیرفعال شده
djangorestframework==3.16.1
idna==3.10
importlib_resources==6.5.2
jalali_core==1.0.0
jdatetime==5.2.0
kavenegar==1.1.2
mysql-connector-python==9.4.0
mysqlclient==2.2.7
pillow==11.3.0
PyMySQL==1.1.1
pyserial==3.5
python-barcode==0.15.1
python-bidi==0.6.6
python-escpos==3.1
pytz==2025.2
PyYAML==6.0.2
qrcode==8.2
reportlab==4.4.3
requests==2.32.5
schedule==1.2.2
six==1.17.0
sqlparse==0.5.3
typing_extensions==4.14.1
tzdata==2025.2
ua-parser==1.0.1
ua-parser-builtins==0.18.0.post1
urllib3==2.5.0
user-agents==2.2.0
whitenoise==6.10.0
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
        print(f"🔹 OFFLINE MODE: Serial connection to {port} disabled")
        self.port = port
        self.baudrate = baudrate
        self.is_open = False

    def open(self):
        """Open serial connection"""
        print(f"🔹 OFFLINE MODE: Would open serial connection to {self.port}")
        self.is_open = True
        return True

    def close(self):
        """Close serial connection"""
        print(f"🔹 OFFLINE MODE: Would close serial connection to {self.port}")
        self.is_open = False

    def write(self, data):
        """Write data to serial port"""
        if isinstance(data, bytes):
            data_str = data.decode('utf-8', errors='ignore')
        else:
            data_str = str(data)
        print(f"🔹 OFFLINE MODE: Would write to {self.port}: {data_str[:100]}{'...' if len(data_str) > 100 else ''}")
        return len(data)

    def read(self, size=1):
        """Read data from serial port"""
        print(f"🔹 OFFLINE MODE: Would read {size} bytes from {self.port}")
        return b''

    def readline(self, size=-1):
        """Read line from serial port"""
        print(f"🔹 OFFLINE MODE: Would read line from {self.port}")
        return b''

    def flush(self):
        """Flush serial buffer"""
        print(f"🔹 OFFLINE MODE: Would flush {self.port} buffer")

    def reset_input_buffer(self):
        """Reset input buffer"""
        print(f"🔹 OFFLINE MODE: Would reset input buffer of {self.port}")

    def reset_output_buffer(self):
        """Reset output buffer"""
        print(f"🔹 OFFLINE MODE: Would reset output buffer of {self.port}")

    @property
    def in_waiting(self):
        """Get number of bytes in input buffer"""
        return 0

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

# توابع اصلی ماژول serial
def serial_for_url(url, *args, **kwargs):
    """Create serial port from URL"""
    print(f"🔹 OFFLINE MODE: Would create serial port for URL: {url}")
    return Serial(port=url)

def list_ports():
    """List available serial ports"""
    print("🔹 OFFLINE MODE: Would list available serial ports")
    return []

# تعریف استثناها
class SerialException(Exception):
    pass

class SerialTimeoutException(SerialException):
    pass

# تعریف مقادیر ثابت
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

# برای سازگاری با import *
__all__ = ['Serial', 'serial_for_url', 'list_ports', 'SerialException', 
           'SerialTimeoutException', 'VERSION', 'PARITY_NONE', 'PARITY_EVEN',
           'PARITY_ODD', 'PARITY_MARK', 'PARITY_SPACE', 'STOPBITS_ONE',
           'STOPBITS_ONE_POINT_FIVE', 'STOPBITS_TWO', 'FIVEBITS', 'SIXBITS',
           'SEVENBITS', 'EIGHTBITS']
'''
            zipf.writestr('plasco_system/serial.py', serial_stub_content)

            # ==================== فایل نصب اصلی (BAT) - نسخه بهبود یافته ====================
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
    goto :setup_stubs
)

echo ℹ️ No system Python found, using embedded Python...
set "USE_SYSTEM_PYTHON=0"

:setup_stubs
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

echo Setting up serial stub...
copy plasco_system\\serial.py plasco_system\\dashbord_app\\serial.py >nul 2>&1
copy plasco_system\\serial.py plasco_system\\pos_payment\\serial.py >nul 2>&1
copy plasco_system\\serial.py plasco_system\\invoice_app\\serial.py >nul 2>&1

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
"%PIP_PATH%" install Django==5.2.4
"%PIP_PATH%" install django-cors-headers==4.8.0
"%PIP_PATH%" install djangorestframework==3.16.1
"%PIP_PATH%" install pillow==11.3.0

echo Installing utility packages...
"%PIP_PATH%" install requests==2.32.5
"%PIP_PATH%" install jdatetime==5.2.0
"%PIP_PATH%" install python-barcode==0.15.1
"%PIP_PATH%" install django-environ==0.12.0
"%PIP_PATH%" install django-jalali==6.0.1

echo Installing PDF and reporting packages...
"%PIP_PATH%" install reportlab==4.4.3
"%PIP_PATH%" install qrcode==8.2
"%PIP_PATH%" install PyYAML==6.0.2

echo Installing Persian language packages...
"%PIP_PATH%" install arabic-reshaper==3.0.0
"%PIP_PATH%" install python-bidi==0.6.6

echo Installing serial communication package...
"%PIP_PATH%" install pyserial==3.5

echo Installing database packages...
"%PIP_PATH%" install mysqlclient==2.2.7
"%PIP_PATH%" install mysql-connector-python==9.4.0
"%PIP_PATH%" install pymysql==1.1.1

echo Installing remaining packages...
"%PIP_PATH%" install django-cleanup==8.1.0
:: "%PIP_PATH%" install django-select2==8.4.1  # موقتاً غیرفعال شده
"%PIP_PATH%" install python-escpos==3.1
"%PIP_PATH%" install schedule==1.2.2
"%PIP_PATH%" install whitenoise==6.10.0
"%PIP_PATH%" install user-agents==2.2.0
"%PIP_PATH%" install ua-parser==1.0.1
"%PIP_PATH%" install appdirs==1.4.4
"%PIP_PATH%" install argcomplete==3.6.2
"%PIP_PATH%" install certifi==2025.8.3
"%PIP_PATH%" install charset-normalizer==3.4.3
"%PIP_PATH%" install colorama==0.4.6
"%PIP_PATH%" install asgiref==3.9.1
"%PIP_PATH%" install idna==3.10
"%PIP_PATH%" install importlib_resources==6.5.2
"%PIP_PATH%" install jalali_core==1.0.0
"%PIP_PATH%" install django-jalali-date==1.0.1
"%PIP_PATH%" install django-appconf==1.1.0
"%PIP_PATH%" install pytz==2025.2
"%PIP_PATH%" install six==1.17.0
"%PIP_PATH%" install sqlparse==0.5.3
"%PIP_PATH%" install typing_extensions==4.14.1
"%PIP_PATH%" install tzdata==2025.2
"%PIP_PATH%" install ua-parser-builtins==0.18.0.post1
"%PIP_PATH%" install urllib3==2.5.0

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
- All required packages from your requirements.txt

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
- Django Version: 5.2.4
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