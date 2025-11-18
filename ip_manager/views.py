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
import tempfile
import logging

# تنظیم لاگر
logger = logging.getLogger(__name__)


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
        logger.error(f"Error in list_ips: {str(e)}")
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

            # اعتبارسنجی فرمت IP
            if not validate_ip_address(ip_address):
                return JsonResponse({'status': 'error', 'message': 'فرمت IP نامعتبر است'})

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
            logger.error(f"Error in add_ip: {str(e)}")
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
        logger.error(f"Error in delete_ip: {str(e)}")
        return JsonResponse({'status': 'error', 'message': f'خطا در حذف IP: {str(e)}'})


@csrf_exempt
def update_ip(request, ip_id):
    """ویرایش IP (API)"""
    if request.method == 'POST':
        try:
            ip = get_object_or_404(AllowedIP, id=ip_id)
            ip_address = request.POST.get('ip_address')
            description = request.POST.get('description', '')

            if not validate_ip_address(ip_address):
                return JsonResponse({'status': 'error', 'message': 'فرمت IP نامعتبر است'})

            if AllowedIP.objects.filter(ip_address=ip_address).exclude(id=ip_id).exists():
                return JsonResponse({'status': 'error', 'message': 'این IP قبلاً ثبت شده است'})

            ip.ip_address = ip_address
            ip.description = description
            ip.save()

            return JsonResponse({'status': 'success', 'message': 'IP با موفقیت ویرایش شد'})
        except Exception as e:
            logger.error(f"Error in update_ip: {str(e)}")
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
            logger.error(f"Error in toggle_ip: {str(e)}")
            return JsonResponse({'status': 'error', 'message': f'خطا در تغییر وضعیت IP: {str(e)}'})
    else:
        return JsonResponse({'status': 'error', 'message': 'متد غیرمجاز'})


def validate_ip_address(ip_address):
    """اعتبارسنجی آدرس IP"""
    import re
    pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if not re.match(pattern, ip_address):
        return False

    # بررسی اینکه هر بخش بین 0-255 باشد
    parts = ip_address.split('.')
    for part in parts:
        if not 0 <= int(part) <= 255:
            return False

    return True


def create_complete_install_package(selected_ips):
    """ایجاد پکیج نصب کامل با تنظیمات آفلاین سفارشی"""
    try:
        BASE_DIR = settings.BASE_DIR

        # ایجاد یک فایل موقت برای ZIP
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
        temp_path = temp_file.name
        temp_file.close()

        logger.info(f"🔹 Creating installation package for IPs: {selected_ips}")

        with zipfile.ZipFile(temp_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            logger.info("📦 Creating complete installation package...")

            # ==================== کپی کردن کل پروژه بدون تغییر ====================

            # فایل manage.py
            manage_path = BASE_DIR / 'manage.py'
            if manage_path.exists():
                zipf.write(manage_path, 'plasco_system/manage.py')
                logger.info("✅ Added: manage.py")

            # پوشه اصلی پروژه (plasco) - تمام فایل‌ها
            plasco_path = BASE_DIR / 'plasco'
            if plasco_path.exists():
                for root, dirs, files in os.walk(plasco_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.join('plasco_system', os.path.relpath(file_path, BASE_DIR))
                        zipf.write(file_path, arcname)
                logger.info("✅ Added plasco folder completely")

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
                            file_path = os.path.join(root, file)
                            arcname = os.path.join('plasco_system', os.path.relpath(file_path, BASE_DIR))
                            zipf.write(file_path, arcname)
                    logger.info(f"✅ Added app: {app}")

            # ==================== فایل‌های قالب و استاتیک ====================

            # پوشه templates
            templates_path = BASE_DIR / 'templates'
            if templates_path.exists():
                for root, dirs, files in os.walk(templates_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.join('plasco_system', os.path.relpath(file_path, BASE_DIR))
                        zipf.write(file_path, arcname)
                logger.info("✅ Added templates folder")

            # پوشه static
            static_path = BASE_DIR / 'static'
            if static_path.exists():
                for root, dirs, files in os.walk(static_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.join('plasco_system', os.path.relpath(file_path, BASE_DIR))
                        zipf.write(file_path, arcname)
                logger.info("✅ Added static folder")

            # ==================== فایل settings_offline.py سفارشی ====================
            settings_content = f'''
"""
Django settings for plasco project.
برای اجرا روی کامپیوترهای داخلی شرکت - حالت آفلاین
"""

from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

# حالت آفلاین
IS_OFFLINE_MODE = True
SECRET_KEY = 'django-insecure-9a=faq-)zl&%@!5(9t8!0r(ar)&()3l+hc#a)+-!eh$-ljkdh@'
DEBUG = True

# لیست IPهای مجاز برای حالت آفلاین - IPهای انتخاب شده اضافه شدند
OFFLINE_ALLOWED_IPS = ['192.168.1.172', '192.168.1.157', '127.0.0.1', 'localhost', '192.168.1.100', '192.168.1.101'] + {selected_ips}
ALLOWED_HOSTS = OFFLINE_ALLOWED_IPS + ['plasmarket.ir', 'www.plasmarket.ir']

print("🟢 اجرا در حالت آفلاین - ديتابيس محلي (Slave)")

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'account_app.apps.AccountAppConfig',
    'dashbord_app.apps.DashbordAppConfig',
    'cantact_app.apps.CantactAppConfig',
    'invoice_app.apps.InvoiceAppConfig',
    'it_app.apps.ItAppConfig',
    'pos_payment.apps.PosPaymentConfig',
    'sync_app',
    'sync_api',
    'control_panel',
    'offline_ins',
    'ip_manager'
]
SESSION_ENGINE = 'django.contrib.sessions.backends.db'  # حتماً از دیتابیس استفاده کنید
SESSION_COOKIE_NAME = 'plasco_session_id'
SESSION_COOKIE_AGE = 3600 * 24  # 24 ساعت
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_SECURE = True  # برای HTTPS
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_SAVE_EVERY_REQUEST = True


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

# دیتابیس SQLite برای حالت آفلاین
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
STATIC_ROOT = '/static/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# تنظیمات همگام‌سازی
SYNC_INTERVAL = 60
ONLINE_SERVER_URL = "https://plasmarket.ir"
OFFLINE_MODE = True
ALLOWED_OFFLINE_IPS = OFFLINE_ALLOWED_IPS

# ⚠️ اضافه کردن این خط جدید برای غیرفعال کردن سرویس خودکار
SYNC_AUTO_START = True  # غیرفعال کردن سرویس سینک خودکار

# غیرفعال کردن چک‌های امنیتی برای نصب آسان
SILENCED_SYSTEM_CHECKS = [
    'security.W001',
    'security.W002', 
    'security.W004', 
    'security.W008', 
    'security.W009',
    'security.W019',
    'security.W020',
    'urls.W005',
]
'''
            zipf.writestr('plasco_system/plasco/settings_offline.py', settings_content.strip())

            # فایل settings.py اصلی که از آفلاین ایمپورت می‌کند
            zipf.writestr('plasco_system/plasco/settings.py', 'from .settings_offline import *\n')

            # ==================== فایل requirements با user-agents ====================
            requirements_content = '''# Plasco Offline System - Python 3.8+ Compatible
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
python-magic==0.4.27
django-import-export==3.3.0
django-cleanup==8.0.0
python-dateutil==2.8.2
pytz==2023.3
pyserial==3.5
pymysql==1.1.0
sqlparse==0.4.4
asgiref==3.7.2
user-agents==2.2.0  # برای middleware
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
        print(f"[ESC/POS SIMULATION] Printing: {text}")

    def cut(self):
        print("[ESC/POS SIMULATION] Paper cut")

    def close(self):
        pass

class Usb:
    def __init__(self, *args, **kwargs):
        pass

    def text(self, text):
        print(f"[ESC/POS SIMULATION] USB Printing: {text}")

    def cut(self):
        print("[ESC/POS SIMULATION] USB Paper cut")

    def close(self):
        pass

class Network:
    def __init__(self, *args, **kwargs):
        pass

    def text(self, text):
        print(f"[ESC/POS SIMULATION] Network Printing: {text}")

    def cut(self):
        print("[ESC/POS SIMULATION] Network Paper cut")

    def close(self):
        pass

class File:
    def __init__(self, *args, **kwargs):
        pass

    def text(self, text):
        print(f"[ESC/POS SIMULATION] File Printing: {text}")

    def cut(self):
        print("[ESC/POS SIMULATION] File Paper cut")

    def close(self):
        pass

__all__ = ['Serial', 'Usb', 'Network', 'File']
'''
            zipf.writestr('plasco_system/escpos.py', escpos_stub_content)
            zipf.writestr('plasco_system/escpos/__init__.py', '')
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
        print(f"[SERIAL SIMULATION] Opened port: {self.port}")
        return True

    def close(self):
        self.is_open = False
        print(f"[SERIAL SIMULATION] Closed port: {self.port}")

    def write(self, data):
        print(f"[SERIAL SIMULATION] Writing data: {data}")
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

            # ==================== فایل نصب اصلی (BAT) - اضافه کردن انتقال خودکار دیتابیس ====================
            main_bat = '''@echo off
chcp 65001
title Plasco Offline System Installer
setlocal enabledelayedexpansion

echo.
echo ============================================
echo    Plasco Offline System - Complete Installer
echo ============================================
echo.

echo Step 1: Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Python not found or not in PATH!
    echo.
    echo Please install Python 3.8+ from:
    echo https://www.python.org/downloads/
    echo.
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [OK] !PYTHON_VERSION! detected
echo.

echo Step 2: Setting up library stubs for offline mode...
mkdir plasco_system\\escpos 2>nul

copy plasco_system\\kavenegar.py plasco_system\\account_app\\kavenegar.py >nul 2>&1
copy plasco_system\\kavenegar.py plasco_system\\cantact_app\\kavenegar.py >nul 2>&1
copy plasco_system\\kavenegar.py plasco_system\\invoice_app\\kavenegar.py >nul 2>&1

copy plasco_system\\escpos.py plasco_system\\dashbord_app\\escpos.py >nul 2>&1
copy plasco_system\\escpos.py plasco_system\\pos_payment\\escpos.py >nul 2>&1
copy plasco_system\\escpos.py plasco_system\\invoice_app\\escpos.py >nul 2>&1

copy plasco_system\\escpos.py plasco_system\\escpos\\__init__.py >nul 2>&1
copy plasco_system\\escpos.py plasco_system\\escpos\\printer.py >nul 2>&1

copy plasco_system\\serial.py plasco_system\\dashbord_app\\serial.py >nul 2>&1
copy plasco_system\\serial.py plasco_system\\pos_payment\\serial.py >nul 2>&1
copy plasco_system\\serial.py plasco_system\\invoice_app\\serial.py >nul 2>&1

echo [OK] Library stubs setup completed
echo.

echo Step 3: Installing required packages...
echo This may take 5-15 minutes. Please wait...
echo.

cd plasco_system

echo Upgrading pip...
python -m pip install --upgrade pip
if %errorlevel% neq 0 (
    echo [ERROR] Failed to upgrade pip
    pause
    exit /b 1
)
echo [OK] pip upgraded successfully

echo Installing packages one by one...
python -m pip install Django==4.2.7
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install Django
    pause
    exit /b 1
)

python -m pip install django-cors-headers==4.3.1
python -m pip install djangorestframework==3.14.0
python -m pip install Pillow==10.0.1
python -m pip install requests==2.31.0
python -m pip install jdatetime==4.1.1
python -m pip install python-barcode==0.15.1
python -m pip install python-decouple==3.8
python -m pip install django-filter==23.3
python -m pip install reportlab==4.0.4
python -m pip install xhtml2pdf==0.2.13
python -m pip install openpyxl==3.1.2
python -m pip install django-jalali==5.0.0
python -m pip install persian==0.3.1
python -m pip install hazm==0.7.0
python -m pip install python-magic==0.4.27
python -m pip install django-import-export==3.3.0
python -m pip install django-cleanup==8.0.0
python -m pip install python-dateutil==2.8.2
python -m pip install pytz==2023.3
python -m pip install pyserial==3.5
python -m pip install pymysql==1.1.0
python -m pip install sqlparse==0.4.4
python -m pip install asgiref==3.7.2
python -m pip install user-agents==2.2.0

echo [OK] All packages installed successfully
echo.

echo Step 4: Setting up database...
echo Creating database migrations...
python manage.py makemigrations --noinput

echo Applying migrations...
python manage.py migrate --run-syncdb
if %errorlevel% neq 0 (
    echo [WARNING] Migration had some issues, trying alternative approach...
    python manage.py migrate --run-syncdb
)

echo [OK] Database setup completed

echo Step 5: Creating admin user...
python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('admin', 'admin@plasco.com', 'admin123') if not User.objects.filter(username='admin').exists() else print('Admin user already exists')"
echo [OK] Admin user setup completed

echo.
echo ============================================
echo    INSTALLATION COMPLETED SUCCESSFULLY!
echo ============================================
echo.
echo [SUCCESS] Plasco Offline System is ready!
echo.
echo 📦 شروع انتقال خودکار دیتابیس از سرور اصلی...
echo.

cd plasco_system

echo 🔄 در حال بررسی اتصال به سرور اصلی...
python manage.py shell -c "
import requests
try:
    response = requests.get('https://plasmarket.ir/', timeout=10)
    print('✅ اتصال به سرور اصلی برقرار است')
    print('🌐 شروع انتقال داده‌ها...')
except:
    print('⚠️ اتصال به سرور اصلی برقرار نیست')
    print('💡 سیستم بدون داده‌های سرور راه‌اندازی می‌شود')
"

echo.
echo 📞 انتقال مخاطبان و شعب...
python manage.py sync_full_cantact || echo ⚠️ خطا در انتقال مخاطبان

echo 💰 انتقال داده‌های مالی...
python manage.py sync_full_account || echo ⚠️ خطا در انتقال داده مالی

echo 📊 انتقال داده‌های داشبورد...
python manage.py sync_full_dashbord || echo ⚠️ خطا در انتقال داشبورد

echo 🧾 انتقال فاکتورها...
python manage.py sync_full_invoice || echo ⚠️ خطا در انتقال فاکتورها

echo 💳 انتقال تراکنش‌ها...
python manage.py sync_full_pos_payment || echo ⚠️ خطا در انتقال تراکنش‌ها

echo.
echo ============================================
echo    نصب و انتقال داده کامل شد!
echo ============================================
echo.

cd plasco_system

echo Access URLs:
echo    Main System: http://localhost:8000
echo    Admin Panel: http://localhost:8000/admin
echo    IP Management: http://localhost:8000/ip/ip_manager/
echo.
echo Admin Credentials:
echo    Username: admin
echo    Password: admin123
echo.
echo Starting server...
echo To stop server, press CTRL+C
echo ============================================
echo.
echo Waiting 5 seconds before starting server...
timeout /t 5 /nobreak >nul

:start_server
echo Starting server on port 8000...
python manage.py runserver 0.0.0.0:8000
if %errorlevel% neq 0 (
    echo.
    echo [WARNING] Port 8000 is busy, trying port 8001...
    echo.
    timeout /t 3 /nobreak >nul
    python manage.py runserver 0.0.0.0:8001
)

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Server startup failed!
    echo.
    echo Troubleshooting steps:
    echo 1. Check if ports 8000-8001 are busy
    echo 2. Try: python manage.py runserver 0.0.0.0:8002
    echo 3. Check firewall settings
    echo.
    pause
)
'''
            zipf.writestr('START_HERE.bat', main_bat)

            # ==================== فایل راهنمای عیب‌یابی ====================
            troubleshooting_content = f'''
Plasco Offline System - Troubleshooting Guide
============================================

System Information:
- Generated: {timezone.now().strftime("%Y/%m/%d %H:%M")}
- Allowed IPs: {", ".join(selected_ips)}
- Python: 3.8+ required

If the script fails:

1. Problem: Window closes quickly
   Solution: Right-click START_HERE.bat and select "Edit"
   Add "pause" at the end to see the error

2. Problem: Python not found
   Solution: 
   - Install Python 3.8+ from: https://python.org/downloads/
   - Check "Add Python to PATH" during installation

3. Problem: Package installation fails
   Solution:
   - Run manually in cmd:
     cd plasco_system
     pip install -r requirements_offline.txt

4. Problem: Port 8000 busy
   Solution:
   - Run manually:
     python manage.py runserver 0.0.0.0:8001

5. Problem: Database migration fails
   Solution:
   - Delete db.sqlite3 file
   - Run: python manage.py migrate

Useful Commands:
- Start server: python manage.py runserver 0.0.0.0:8000
- Create admin: python manage.py createsuperuser
- Check migrations: python manage.py showmigrations
- Make migrations: python manage.py makemigrations

Common Issues:
- If "python-magic" fails on Windows, install manually:
  pip install python-magic-bin
- If "hazm" fails, try:
  pip install hazm --no-deps
- For Persian text issues, ensure UTF-8 encoding
'''
            zipf.writestr('TROUBLESHOOTING.txt', troubleshooting_content)

            # ==================== فایل راهنما ====================
            readme_content = f'''
Plasco Offline System - Complete Standalone Installation
=======================================================

Quick Start:
1. Extract ALL files to a folder
2. Double-click "START_HERE.bat"
3. Wait for automatic installation (5-15 minutes)
4. System will start automatically

Access Information:
- Main Application: http://localhost:8000
- Admin Panel: http://localhost:8000/admin
- IP Management: http://localhost:8000/ip/ip_manager/
- Admin Username: admin
- Admin Password: admin123

System Requirements:
- Windows 7/8/10/11
- Python 3.8+ (automatically checked)
- 2GB RAM minimum
- 500MB free disk space

Features:
✅ Complete system functionality
✅ Persian language support
✅ SQLite database
✅ Automatic package installation
✅ Admin user creation
✅ IP access management

Limitations in Offline Mode:
❌ SMS functionality disabled
❌ Printer functionality disabled (simulated)
❌ External API calls disabled
❌ Real serial communication disabled

Allowed IP Addresses:
{chr(10).join(f"   - {ip}" for ip in selected_ips)}

Support:
- Created: {timezone.now().strftime("%Y/%m/%d %H:%M")}
- This is a fully self-contained offline system

Troubleshooting:
- If installation fails, see TROUBLESHOOTING.txt
- If port 8000 is busy, system will use port 8001
- First run may take 5-15 minutes
- Ensure no antivirus is blocking the installation
'''
            zipf.writestr('README_FIRST.txt', readme_content)

        logger.info(f"✅ ZIP file created successfully: {temp_path}")

        # خواندن محتوای فایل ZIP
        with open(temp_path, 'rb') as f:
            zip_content = f.read()

        # حذف فایل موقت
        os.unlink(temp_path)

        return zip_content

    except Exception as e:
        logger.error(f"❌ Error in create_complete_install_package: {str(e)}")
        # تمیزکاری فایل موقت در صورت خطا
        try:
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.unlink(temp_path)
        except Exception as cleanup_error:
            logger.error(f"❌ Cleanup error: {cleanup_error}")

        return None


# def create_complete_install_package(selected_ips):
#     """ایجاد پکیج نصب کامل با تنظیمات آفلاین سفارشی"""
#     try:
#         BASE_DIR = settings.BASE_DIR
#
#         # ایجاد یک فایل موقت برای ZIP
#         temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
#         temp_path = temp_file.name
#         temp_file.close()
#
#         logger.info(f"🔹 Creating installation package for IPs: {selected_ips}")
#
#         with zipfile.ZipFile(temp_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
#             logger.info("📦 Creating complete installation package...")
#
#             # ==================== کپی کردن کل پروژه بدون تغییر ====================
#
#             # فایل manage.py
#             manage_path = BASE_DIR / 'manage.py'
#             if manage_path.exists():
#                 zipf.write(manage_path, 'plasco_system/manage.py')
#                 logger.info("✅ Added: manage.py")
#
#             # پوشه اصلی پروژه (plasco) - تمام فایل‌ها
#             plasco_path = BASE_DIR / 'plasco'
#             if plasco_path.exists():
#                 for root, dirs, files in os.walk(plasco_path):
#                     for file in files:
#                         file_path = os.path.join(root, file)
#                         arcname = os.path.join('plasco_system', os.path.relpath(file_path, BASE_DIR))
#                         zipf.write(file_path, arcname)
#                 logger.info("✅ Added plasco folder completely")
#
#             # ==================== تمام اپلیکیشن‌ها ====================
#             app_folders = [
#                 'account_app', 'dashbord_app', 'cantact_app', 'invoice_app',
#                 'it_app', 'pos_payment', 'sync_app', 'sync_api',
#                 'control_panel', 'offline_ins', 'home_app', 'ip_manager'
#             ]
#
#             for app in app_folders:
#                 app_path = BASE_DIR / app
#                 if app_path.exists():
#                     for root, dirs, files in os.walk(app_path):
#                         for file in files:
#                             file_path = os.path.join(root, file)
#                             arcname = os.path.join('plasco_system', os.path.relpath(file_path, BASE_DIR))
#                             zipf.write(file_path, arcname)
#                     logger.info(f"✅ Added app: {app}")
#
#             # ==================== فایل‌های قالب و استاتیک ====================
#
#             # پوشه templates
#             templates_path = BASE_DIR / 'templates'
#             if templates_path.exists():
#                 for root, dirs, files in os.walk(templates_path):
#                     for file in files:
#                         file_path = os.path.join(root, file)
#                         arcname = os.path.join('plasco_system', os.path.relpath(file_path, BASE_DIR))
#                         zipf.write(file_path, arcname)
#                 logger.info("✅ Added templates folder")
#
#             # پوشه static
#             static_path = BASE_DIR / 'static'
#             if static_path.exists():
#                 for root, dirs, files in os.walk(static_path):
#                     for file in files:
#                         file_path = os.path.join(root, file)
#                         arcname = os.path.join('plasco_system', os.path.relpath(file_path, BASE_DIR))
#                         zipf.write(file_path, arcname)
#                 logger.info("✅ Added static folder")
#
#             # ==================== فایل settings_offline.py سفارشی ====================
#             settings_content = f'''
# """
# Django settings for plasco project.
# برای اجرا روی کامپیوترهای داخلی شرکت - حالت آفلاین
# """
#
# from pathlib import Path
# import os
#
# BASE_DIR = Path(__file__).resolve().parent.parent
#
# # حالت آفلاین
# IS_OFFLINE_MODE = True
# SECRET_KEY = 'django-insecure-9a=faq-)zl&%@!5(9t8!0r(ar)&()3l+hc#a)+-!eh$-ljkdh@'
# DEBUG = True
#
# # لیست IPهای مجاز برای حالت آفلاین - IPهای انتخاب شده اضافه شدند
# OFFLINE_ALLOWED_IPS = ['192.168.1.172', '192.168.1.157', '127.0.0.1', 'localhost', '192.168.1.100', '192.168.1.101'] + {selected_ips}
# ALLOWED_HOSTS = OFFLINE_ALLOWED_IPS + ['plasmarket.ir', 'www.plasmarket.ir']
#
# print("🟢 اجرا در حالت آفلاین - ديتابيس محلي (Slave)")
#
# INSTALLED_APPS = [
#     'django.contrib.admin',
#     'django.contrib.auth',
#     'django.contrib.contenttypes',
#     'django.contrib.sessions',
#     'django.contrib.messages',
#     'django.contrib.staticfiles',
#     'rest_framework',
#     'rest_framework.authtoken',
#     'corsheaders',
#     'account_app.apps.AccountAppConfig',
#     'dashbord_app.apps.DashbordAppConfig',
#     'cantact_app.apps.CantactAppConfig',
#     'invoice_app.apps.InvoiceAppConfig',
#     'it_app.apps.ItAppConfig',
#     'pos_payment.apps.PosPaymentConfig',
#     'sync_app',
#     'sync_api',
#     'control_panel',
#     'offline_ins',
#     'ip_manager'
# ]
# SESSION_ENGINE = 'django.contrib.sessions.backends.db'  # حتماً از دیتابیس استفاده کنید
# SESSION_COOKIE_NAME = 'plasco_session_id'
# SESSION_COOKIE_AGE = 3600 * 24  # 24 ساعت
# SESSION_EXPIRE_AT_BROWSER_CLOSE = True
# SESSION_COOKIE_SECURE = True  # برای HTTPS
# SESSION_COOKIE_HTTPONLY = True
# SESSION_COOKIE_SAMESITE = 'Lax'
# SESSION_SAVE_EVERY_REQUEST = True
#
#
# MIDDLEWARE = [
#     'corsheaders.middleware.CorsMiddleware',
#     'django.middleware.security.SecurityMiddleware',
#     'django.contrib.sessions.middleware.SessionMiddleware',
#     'django.middleware.common.CommonMiddleware',
#     'django.middleware.csrf.CsrfViewMiddleware',
#     'django.contrib.auth.middleware.AuthenticationMiddleware',
#     'django.contrib.messages.middleware.MessageMiddleware',
#     'django.middleware.clickjacking.XFrameOptionsMiddleware',
# ]
#
# ROOT_URLCONF = 'plasco.urls'
#
# TEMPLATES = [
#     {{
#         'BACKEND': 'django.template.backends.django.DjangoTemplates',
#         'DIRS': [BASE_DIR / 'templates'],
#         'APP_DIRS': True,
#         'OPTIONS': {{
#             'context_processors': [
#                 'django.template.context_processors.request',
#                 'django.contrib.auth.context_processors.auth',
#                 'django.contrib.messages.context_processors.messages',
#             ],
#         }},
#     }},
# ]
#
# WSGI_APPLICATION = 'plasco.wsgi.application'
#
# # دیتابیس SQLite برای حالت آفلاین
# DATABASES = {{
#     'default': {{
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db_offline.sqlite3',
#     }}
# }}
#
# AUTH_PASSWORD_VALIDATORS = [
#     {{
#         'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
#     }},
#     {{
#         'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
#     }},
#     {{
#         'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
#     }},
#     {{
#         'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
#     }},
# ]
#
# LANGUAGE_CODE = 'fa-ir'
# TIME_ZONE = 'Asia/Tehran'
# USE_I18N = True
# USE_TZ = True
#
# STATIC_URL = '/static/'
# MEDIA_URL = '/media/'
# STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
# STATIC_ROOT = '/static/'
# MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
#
# DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
#
# # تنظیمات همگام‌سازی
# SYNC_INTERVAL = 60
# ONLINE_SERVER_URL = "https://plasmarket.ir"
# OFFLINE_MODE = True
# ALLOWED_OFFLINE_IPS = OFFLINE_ALLOWED_IPS
#
# # ⚠️ اضافه کردن این خط جدید برای غیرفعال کردن سرویس خودکار
# SYNC_AUTO_START = True  # غیرفعال کردن سرویس سینک خودکار
#
# # غیرفعال کردن چک‌های امنیتی برای نصب آسان
# SILENCED_SYSTEM_CHECKS = [
#     'security.W001',
#     'security.W002',
#     'security.W004',
#     'security.W008',
#     'security.W009',
#     'security.W019',
#     'security.W020',
#     'urls.W005',
# ]
# '''
#             zipf.writestr('plasco_system/plasco/settings_offline.py', settings_content.strip())
#
#             # فایل settings.py اصلی که از آفلاین ایمپورت می‌کند
#             zipf.writestr('plasco_system/plasco/settings.py', 'from .settings_offline import *\n')
#
#             # ==================== فایل requirements با user-agents ====================
#             requirements_content = '''# Plasco Offline System - Python 3.8+ Compatible
# Django==4.2.7
# django-cors-headers==4.3.1
# djangorestframework==3.14.0
# Pillow==10.0.1
# requests==2.31.0
# jdatetime==4.1.1
# python-barcode==0.15.1
# python-decouple==3.8
# django-filter==23.3
# reportlab==4.0.4
# xhtml2pdf==0.2.13
# openpyxl==3.1.2
# django-jalali==5.0.0
# persian==0.3.1
# hazm==0.7.0
# python-magic==0.4.27
# django-import-export==3.3.0
# django-cleanup==8.0.0
# python-dateutil==2.8.2
# pytz==2023.3
# pyserial==3.5
# pymysql==1.1.0
# sqlparse==0.4.4
# asgiref==3.7.2
# user-agents==2.2.0  # برای middleware
# '''
#             zipf.writestr('plasco_system/requirements_offline.txt', requirements_content)
#
#             # ==================== فایل‌های جایگزین برای کتابخانه‌های مشکل‌ساز ====================
#
#             # ماژول جایگزین kavenegar
#             kavenegar_stub_content = '''
# """
# ماژول جایگزین برای kavenegar - برای حالت آفلاین
# """
#
# class KavenegarAPI:
#     def __init__(self, *args, **kwargs):
#         pass
#
#     def sms_send(self, *args, **kwargs):
#         return {"status": 200, "message": "SMS disabled in offline mode"}
#
#     def call_make(self, *args, **kwargs):
#         return {"status": 200, "message": "Calls disabled in offline mode"}
#
#     def verify_lookup(self, *args, **kwargs):
#         return {"status": 200, "message": "Verify lookup disabled in offline mode"}
#
# class KavenegarException(Exception):
#     pass
#
# def send_sms(api_key, sender, receptor, message):
#     return {"status": 200, "message": "SMS disabled in offline mode"}
#
# def send_lookup_sms(api_key, receptor, token, token2, token3, template):
#     return {"status": 200, "message": "Lookup SMS disabled in offline mode"}
#
# __all__ = ['KavenegarAPI', 'KavenegarException', 'send_sms', 'send_lookup_sms']
# '''
#             zipf.writestr('plasco_system/kavenegar.py', kavenegar_stub_content)
#
#             # ماژول جایگزین escpos
#             escpos_stub_content = '''
# """
# ماژول جایگزین برای escpos - برای حالت آفلاین
# """
#
# class Serial:
#     def __init__(self, *args, **kwargs):
#         pass
#
#     def text(self, text):
#         print(f"[ESC/POS SIMULATION] Printing: {text}")
#
#     def cut(self):
#         print("[ESC/POS SIMULATION] Paper cut")
#
#     def close(self):
#         pass
#
# class Usb:
#     def __init__(self, *args, **kwargs):
#         pass
#
#     def text(self, text):
#         print(f"[ESC/POS SIMULATION] USB Printing: {text}")
#
#     def cut(self):
#         print("[ESC/POS SIMULATION] USB Paper cut")
#
#     def close(self):
#         pass
#
# class Network:
#     def __init__(self, *args, **kwargs):
#         pass
#
#     def text(self, text):
#         print(f"[ESC/POS SIMULATION] Network Printing: {text}")
#
#     def cut(self):
#         print("[ESC/POS SIMULATION] Network Paper cut")
#
#     def close(self):
#         pass
#
# class File:
#     def __init__(self, *args, **kwargs):
#         pass
#
#     def text(self, text):
#         print(f"[ESC/POS SIMULATION] File Printing: {text}")
#
#     def cut(self):
#         print("[ESC/POS SIMULATION] File Paper cut")
#
#     def close(self):
#         pass
#
# __all__ = ['Serial', 'Usb', 'Network', 'File']
# '''
#             zipf.writestr('plasco_system/escpos.py', escpos_stub_content)
#             zipf.writestr('plasco_system/escpos/__init__.py', '')
#             zipf.writestr('plasco_system/escpos/printer.py', escpos_stub_content)
#
#             # ماژول جایگزین برای serial (pyserial)
#             serial_stub_content = '''
# """
# ماژول جایگزین برای pyserial - برای حالت آفلاین
# """
#
# class Serial:
#     def __init__(self, port=None, baudrate=9600, bytesize=8, parity='N',
#                  stopbits=1, timeout=None, xonxoff=False, rtscts=False,
#                  write_timeout=None, dsrdtr=False, inter_byte_timeout=None,
#                  exclusive=None, **kwargs):
#         self.port = port
#         self.baudrate = baudrate
#         self.is_open = False
#
#     def open(self):
#         self.is_open = True
#         print(f"[SERIAL SIMULATION] Opened port: {self.port}")
#         return True
#
#     def close(self):
#         self.is_open = False
#         print(f"[SERIAL SIMULATION] Closed port: {self.port}")
#
#     def write(self, data):
#         print(f"[SERIAL SIMULATION] Writing data: {data}")
#         return len(data)
#
#     def read(self, size=1):
#         return b''
#
#     def readline(self, size=-1):
#         return b''
#
#     def flush(self):
#         pass
#
#     def reset_input_buffer(self):
#         pass
#
#     def reset_output_buffer(self):
#         pass
#
#     @property
#     def in_waiting(self):
#         return 0
#
#     def __enter__(self):
#         self.open()
#         return self
#
#     def __exit__(self, exc_type, exc_val, exc_tb):
#         self.close()
#
# def serial_for_url(url, *args, **kwargs):
#     return Serial(port=url)
#
# def list_ports():
#     return []
#
# class SerialException(Exception):
#     pass
#
# class SerialTimeoutException(SerialException):
#     pass
#
# VERSION = "3.5"
# PARITY_NONE = 'N'
# PARITY_EVEN = 'E'
# PARITY_ODD = 'O'
# PARITY_MARK = 'M'
# PARITY_SPACE = 'S'
# STOPBITS_ONE = 1
# STOPBITS_ONE_POINT_FIVE = 1.5
# STOPBITS_TWO = 2
# FIVEBITS = 5
# SIXBITS = 6
# SEVENBITS = 7
# EIGHTBITS = 8
#
# __all__ = ['Serial', 'serial_for_url', 'list_ports', 'SerialException',
#            'SerialTimeoutException', 'VERSION', 'PARITY_NONE', 'PARITY_EVEN',
#            'PARITY_ODD', 'PARITY_MARK', 'PARITY_SPACE', 'STOPBITS_ONE',
#            'STOPBITS_ONE_POINT_FIVE', 'STOPBITS_TWO', 'FIVEBITS', 'SIXBITS',
#            'SEVENBITS', 'EIGHTBITS']
# '''
#             zipf.writestr('plasco_system/serial.py', serial_stub_content)
#
#             # ==================== فایل نصب اصلی (BAT) ====================
#             main_bat = '''@echo off
# chcp 65001
# title Plasco Offline System Installer
# setlocal enabledelayedexpansion
#
# echo.
# echo ============================================
# echo    Plasco Offline System - Complete Installer
# echo ============================================
# echo.
#
# echo Step 1: Checking Python installation...
# python --version >nul 2>&1
# if %errorlevel% neq 0 (
#     echo.
#     echo [ERROR] Python not found or not in PATH!
#     echo.
#     echo Please install Python 3.8+ from:
#     echo https://www.python.org/downloads/
#     echo.
#     echo Make sure to check "Add Python to PATH" during installation.
#     echo.
#     pause
#     exit /b 1
# )
#
# for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
# echo [OK] !PYTHON_VERSION! detected
# echo.
#
# echo Step 2: Setting up library stubs for offline mode...
# mkdir plasco_system\\escpos 2>nul
#
# copy plasco_system\\kavenegar.py plasco_system\\account_app\\kavenegar.py >nul 2>&1
# copy plasco_system\\kavenegar.py plasco_system\\cantact_app\\kavenegar.py >nul 2>&1
# copy plasco_system\\kavenegar.py plasco_system\\invoice_app\\kavenegar.py >nul 2>&1
#
# copy plasco_system\\escpos.py plasco_system\\dashbord_app\\escpos.py >nul 2>&1
# copy plasco_system\\escpos.py plasco_system\\pos_payment\\escpos.py >nul 2>&1
# copy plasco_system\\escpos.py plasco_system\\invoice_app\\escpos.py >nul 2>&1
#
# copy plasco_system\\escpos.py plasco_system\\escpos\\__init__.py >nul 2>&1
# copy plasco_system\\escpos.py plasco_system\\escpos\\printer.py >nul 2>&1
#
# copy plasco_system\\serial.py plasco_system\\dashbord_app\\serial.py >nul 2>&1
# copy plasco_system\\serial.py plasco_system\\pos_payment\\serial.py >nul 2>&1
# copy plasco_system\\serial.py plasco_system\\invoice_app\\serial.py >nul 2>&1
#
# echo [OK] Library stubs setup completed
# echo.
#
# echo Step 3: Installing required packages...
# echo This may take 5-15 minutes. Please wait...
# echo.
#
# cd plasco_system
#
# echo Upgrading pip...
# python -m pip install --upgrade pip
# if %errorlevel% neq 0 (
#     echo [ERROR] Failed to upgrade pip
#     pause
#     exit /b 1
# )
# echo [OK] pip upgraded successfully
#
# echo Installing packages one by one...
# python -m pip install Django==4.2.7
# if %errorlevel% neq 0 (
#     echo [ERROR] Failed to install Django
#     pause
#     exit /b 1
# )
#
# python -m pip install django-cors-headers==4.3.1
# python -m pip install djangorestframework==3.14.0
# python -m pip install Pillow==10.0.1
# python -m pip install requests==2.31.0
# python -m pip install jdatetime==4.1.1
# python -m pip install python-barcode==0.15.1
# python -m pip install python-decouple==3.8
# python -m pip install django-filter==23.3
# python -m pip install reportlab==4.0.4
# python -m pip install xhtml2pdf==0.2.13
# python -m pip install openpyxl==3.1.2
# python -m pip install django-jalali==5.0.0
# python -m pip install persian==0.3.1
# python -m pip install hazm==0.7.0
# python -m pip install python-magic==0.4.27
# python -m pip install django-import-export==3.3.0
# python -m pip install django-cleanup==8.0.0
# python -m pip install python-dateutil==2.8.2
# python -m pip install pytz==2023.3
# python -m pip install pyserial==3.5
# python -m pip install pymysql==1.1.0
# python -m pip install sqlparse==0.4.4
# python -m pip install asgiref==3.7.2
# python -m pip install user-agents==2.2.0
#
# echo [OK] All packages installed successfully
# echo.
#
# echo Step 4: Setting up database...
# echo Creating database migrations...
# python manage.py makemigrations --noinput
#
# echo Applying migrations...
# python manage.py migrate --run-syncdb
# if %errorlevel% neq 0 (
#     echo [WARNING] Migration had some issues, trying alternative approach...
#     python manage.py migrate --run-syncdb
# )
#
# echo [OK] Database setup completed
#
# echo Step 5: Creating admin user...
# python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('admin', 'admin@plasco.com', 'admin123') if not User.objects.filter(username='admin').exists() else print('Admin user already exists')"
# echo [OK] Admin user setup completed
#
# echo.
# echo ============================================
# echo    INSTALLATION COMPLETED SUCCESSFULLY!
# echo ============================================
# echo.
# echo [SUCCESS] Plasco Offline System is ready!
# echo.
# echo Access URLs:
# echo    Main System: http://localhost:8000
# echo    Admin Panel: http://localhost:8000/admin
# echo    IP Management: http://localhost:8000/ip/ip_manager/
# echo.
# echo Admin Credentials:
# echo    Username: admin
# echo    Password: admin123
# echo.
# echo Starting server...
# echo To stop server, press CTRL+C
# echo ============================================
# echo.
# echo Waiting 5 seconds before starting server...
# timeout /t 5 /nobreak >nul
#
# :start_server
# echo Starting server on port 8000...
# python manage.py runserver 0.0.0.0:8000
# if %errorlevel% neq 0 (
#     echo.
#     echo [WARNING] Port 8000 is busy, trying port 8001...
#     echo.
#     timeout /t 3 /nobreak >nul
#     python manage.py runserver 0.0.0.0:8001
# )
#
# if %errorlevel% neq 0 (
#     echo.
#     echo [ERROR] Server startup failed!
#     echo.
#     echo Troubleshooting steps:
#     echo 1. Check if ports 8000-8001 are busy
#     echo 2. Try: python manage.py runserver 0.0.0.0:8002
#     echo 3. Check firewall settings
#     echo.
#     pause
# )
# '''
#             zipf.writestr('START_HERE.bat', main_bat)
#
#             # ==================== فایل راهنمای عیب‌یابی ====================
#             troubleshooting_content = f'''
# Plasco Offline System - Troubleshooting Guide
# ============================================
#
# System Information:
# - Generated: {timezone.now().strftime("%Y/%m/%d %H:%M")}
# - Allowed IPs: {", ".join(selected_ips)}
# - Python: 3.8+ required
#
# If the script fails:
#
# 1. Problem: Window closes quickly
#    Solution: Right-click START_HERE.bat and select "Edit"
#    Add "pause" at the end to see the error
#
# 2. Problem: Python not found
#    Solution:
#    - Install Python 3.8+ from: https://python.org/downloads/
#    - Check "Add Python to PATH" during installation
#
# 3. Problem: Package installation fails
#    Solution:
#    - Run manually in cmd:
#      cd plasco_system
#      pip install -r requirements_offline.txt
#
# 4. Problem: Port 8000 busy
#    Solution:
#    - Run manually:
#      python manage.py runserver 0.0.0.0:8001
#
# 5. Problem: Database migration fails
#    Solution:
#    - Delete db.sqlite3 file
#    - Run: python manage.py migrate
#
# Useful Commands:
# - Start server: python manage.py runserver 0.0.0.0:8000
# - Create admin: python manage.py createsuperuser
# - Check migrations: python manage.py showmigrations
# - Make migrations: python manage.py makemigrations
#
# Common Issues:
# - If "python-magic" fails on Windows, install manually:
#   pip install python-magic-bin
# - If "hazm" fails, try:
#   pip install hazm --no-deps
# - For Persian text issues, ensure UTF-8 encoding
# '''
#             zipf.writestr('TROUBLESHOOTING.txt', troubleshooting_content)
#
#             # ==================== فایل راهنما ====================
#             readme_content = f'''
# Plasco Offline System - Complete Standalone Installation
# =======================================================
#
# Quick Start:
# 1. Extract ALL files to a folder
# 2. Double-click "START_HERE.bat"
# 3. Wait for automatic installation (5-15 minutes)
# 4. System will start automatically
#
# Access Information:
# - Main Application: http://localhost:8000
# - Admin Panel: http://localhost:8000/admin
# - IP Management: http://localhost:8000/ip/ip_manager/
# - Admin Username: admin
# - Admin Password: admin123
#
# System Requirements:
# - Windows 7/8/10/11
# - Python 3.8+ (automatically checked)
# - 2GB RAM minimum
# - 500MB free disk space
#
# Features:
# ✅ Complete system functionality
# ✅ Persian language support
# ✅ SQLite database
# ✅ Automatic package installation
# ✅ Admin user creation
# ✅ IP access management
#
# Limitations in Offline Mode:
# ❌ SMS functionality disabled
# ❌ Printer functionality disabled (simulated)
# ❌ External API calls disabled
# ❌ Real serial communication disabled
#
# Allowed IP Addresses:
# {chr(10).join(f"   - {ip}" for ip in selected_ips)}
#
# Support:
# - Created: {timezone.now().strftime("%Y/%m/%d %H:%M")}
# - This is a fully self-contained offline system
#
# Troubleshooting:
# - If installation fails, see TROUBLESHOOTING.txt
# - If port 8000 is busy, system will use port 8001
# - First run may take 5-15 minutes
# - Ensure no antivirus is blocking the installation
# '''
#             zipf.writestr('README_FIRST.txt', readme_content)
#
#         logger.info(f"✅ ZIP file created successfully: {temp_path}")
#
#         # خواندن محتوای فایل ZIP
#         with open(temp_path, 'rb') as f:
#             zip_content = f.read()
#
#         # حذف فایل موقت
#         os.unlink(temp_path)
#
#         return zip_content
#
#     except Exception as e:
#         logger.error(f"❌ Error in create_complete_install_package: {str(e)}")
#         # تمیزکاری فایل موقت در صورت خطا
#         try:
#             if 'temp_path' in locals() and os.path.exists(temp_path):
#                 os.unlink(temp_path)
#         except Exception as cleanup_error:
#             logger.error(f"❌ Cleanup error: {cleanup_error}")
#         return None

@csrf_exempt
def create_offline_installer(request):
    """ایجاد و دانلود فایل نصب"""
    if request.method == 'POST':
        try:
            selected_ips_json = request.POST.get('selected_ips', '[]')
            selected_ips = json.loads(selected_ips_json)

            if not selected_ips:
                return JsonResponse({
                    'status': 'error',
                    'message': 'لطفاً حداقل یک IP انتخاب کنید'
                })

            logger.info(f"Creating installer for IPs: {selected_ips}")

            # اعتبارسنجی IPهای انتخاب شده
            valid_ips = []
            for ip in selected_ips:
                if validate_ip_address(ip):
                    valid_ips.append(ip)
                else:
                    logger.warning(f"Invalid IP address skipped: {ip}")

            if not valid_ips:
                return JsonResponse({
                    'status': 'error',
                    'message': 'هیچ IP معتبری انتخاب نشده است'
                })

            # ایجاد پکیج
            zip_content = create_complete_install_package(valid_ips)

            if not zip_content:
                return JsonResponse({
                    'status': 'error',
                    'message': 'خطا در ایجاد فایل نصب'
                })

            # ایجاد پاسخ
            response = HttpResponse(zip_content, content_type='application/zip')
            response['Content-Disposition'] = 'attachment; filename="plasco_offline_system.zip"'
            response['Content-Length'] = len(zip_content)

            logger.info("✅ Installer created and sent successfully")
            return response

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': 'خطا در پردازش داده‌های ارسالی'
            })
        except Exception as e:
            logger.error(f"Error in create_offline_installer: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': f'خطا در ایجاد فایل نصب: {str(e)}'
            })

    return JsonResponse({'status': 'error', 'message': 'متد غیرمجاز'})


def test_system_status(request):
    """تست وضعیت سیستم"""
    try:
        # بررسی اتصال به دیتابیس
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")

        # بررسی وجود مدل‌ها
        ip_count = AllowedIP.objects.count()

        return JsonResponse({
            'status': 'success',
            'message': 'سیستم در وضعیت سالم قرار دارد',
            'database': 'connected',
            'ip_count': ip_count,
            'timestamp': timezone.now().isoformat()
        })
    except Exception as e:
        logger.error(f"System status check failed: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': f'خطا در بررسی وضعیت سیستم: {str(e)}'
        })


def download_manual_install_guide(request):
    """دانلود راهنمای نصب دستی"""
    guide_content = '''
Plasco Offline System - Manual Installation Guide
================================================

If the automatic installer fails, follow these steps:

1. Extract the ZIP file to a folder
2. Open Command Prompt as Administrator
3. Navigate to the plasco_system folder
4. Run these commands one by one:

   pip install -r requirements_offline.txt
   python manage.py makemigrations
   python manage.py migrate
   python manage.py createsuperuser
   python manage.py runserver 0.0.0.0:8000

5. Access the system at http://localhost:8000

For specific errors:

- Port already in use: Use different port (8001, 8002, etc.)
- Database errors: Delete db.sqlite3 and run migrations again
- Package errors: Install packages individually
- Permission errors: Run as Administrator

Contact support if issues persist.
'''

    response = HttpResponse(guide_content, content_type='text/plain')
    response['Content-Disposition'] = 'attachment; filename="manual_install_guide.txt"'
    return response