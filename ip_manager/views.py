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
    """ایجاد پکیج نصب کامل - نسخه اصلاح شده"""
    try:
        BASE_DIR = settings.BASE_DIR
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
        temp_path = temp_file.name
        temp_file.close()

        logger.info(f"Creating installation package for IPs: {selected_ips}")

        with zipfile.ZipFile(temp_path, 'w', zipfile.ZIP_DEFLATED) as zipf:

            # ==================== فایل‌های اصلی پروژه ====================
            # [کدهای کپی کردن فایل‌ها مثل قبل...]

            # ==================== فایل urls.py کاملاً اصلاح شده ====================
            urls_content = '''
from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse

def home_view(request):
    return HttpResponse("""
    <html>
        <head>
            <title>Plasco Offline System</title>
            <meta charset="utf-8">
            <style>
                body { 
                    font-family: Tahoma, Arial, sans-serif; 
                    text-align: center; 
                    padding: 50px; 
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    min-height: 100vh;
                    margin: 0;
                }
                .container { 
                    background: rgba(255,255,255,0.1); 
                    padding: 40px; 
                    border-radius: 15px; 
                    backdrop-filter: blur(10px);
                    border: 1px solid rgba(255,255,255,0.2);
                    max-width: 800px;
                    margin: 0 auto;
                }
                .success { 
                    color: #4CAF50; 
                    font-size: 28px; 
                    margin-bottom: 20px;
                }
                .info { 
                    color: #E3F2FD; 
                    margin: 20px 0; 
                    line-height: 1.6;
                }
                ul { 
                    list-style: none; 
                    padding: 0; 
                    margin: 20px 0;
                }
                li { 
                    margin: 10px 0; 
                    font-size: 18px;
                }
                a { 
                    color: #FFD54F; 
                    text-decoration: none;
                    font-weight: bold;
                }
                a:hover { 
                    text-decoration: underline;
                }
                .credential-box {
                    background: rgba(255,255,255,0.2);
                    padding: 15px;
                    border-radius: 8px;
                    margin: 20px 0;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1 class="success">✅ Plasco Offline System Installed Successfully!</h1>
                <div class="info">
                    <p><strong>System is running in OFFLINE MODE</strong></p>
                    <p>Access URLs:</p>
                    <ul>
                        <li>🏠 Main System: <a href="/">Home Page</a></li>
                        <li>⚙️ Admin Panel: <a href="/admin/">Admin</a></li>
                        <li>🔧 IP Management: <a href="/ip/ip_manager/">Manage IPs</a></li>
                    </ul>
                    <div class="credential-box">
                        <p><strong>Admin Credentials:</strong></p>
                        <p>Username: <strong>admin</strong></p>
                        <p>Password: <strong>admin123</strong></p>
                    </div>
                    <p>First run may take a few minutes to complete setup.</p>
                </div>
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

            # ==================== ایجاد فایل urls.py برای ip_manager ====================
            ip_manager_urls_content = '''
from django.urls import path
from .views import (
    manage_ips, list_ips, add_ip, delete_ip,
    update_ip, toggle_ip, create_offline_installer
)

urlpatterns = [
    path('ip_manager/', manage_ips, name='manage_ips'),
    path('ip_manager/api/list/', list_ips, name='list_ips'),
    path('ip_manager/api/add/', add_ip, name='add_ip'),
    path('ip_manager/api/delete/<int:ip_id>/', delete_ip, name='delete_ip'),
    path('ip_manager/api/update/<int:ip_id>/', update_ip, name='update_ip'),
    path('ip_manager/api/toggle/<int:ip_id>/', toggle_ip, name='toggle_ip'),
    path('ip_manager/api/create-offline-installer/', create_offline_installer, name='create_offline_installer'),
]
'''
            zipf.writestr('plasco_system/ip_manager/urls.py', ip_manager_urls_content)

            # ==================== حذف کامل offline_ins از پکیج ====================
            # این بخش را کاملاً حذف کنید یا کامنت کنید
            # هیچ فایل urls.py برای offline_ins ایجاد نکنید

            # ==================== فایل settings_offline.py بدون offline_ins ====================
            settings_content = f'''
"""
Django settings for plasco project - OFFLINE MODE
Compatible with Python 3.8+
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

# فقط اپلیکیشن‌های ضروری - offline_ins حذف شده
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
    'ip_manager',  # فقط این اپ ضروری است
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

DATABASES = {{
    'default': {{
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
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

# غیرفعال کردن چک‌های امنیتی برای نصب آسان
SILENCED_SYSTEM_CHECKS = [
    'security.W001',
    'security.W002', 
    'security.W004', 
    'security.W008', 
    'security.W009',
    'security.W019',
    'security.W020',
]

OFFLINE_MODE = True

print("🟢 Plasco Offline Mode - Minimal configuration for easy installation")
'''
            zipf.writestr('plasco_system/plasco/settings_offline.py', settings_content.strip())
            zipf.writestr('plasco_system/plasco/settings.py', 'from .settings_offline import *\n')

            # بقیه فایل‌ها (requirements, BAT, etc.) مانند قبل...

        # خواندن و بازگرداندن محتوای فایل ZIP
        with open(temp_path, 'rb') as f:
            zip_content = f.read()

        os.unlink(temp_path)
        return zip_content

    except Exception as e:
        logger.error(f"Error creating package: {str(e)}")
        try:
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.unlink(temp_path)
        except:
            pass
        return None

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