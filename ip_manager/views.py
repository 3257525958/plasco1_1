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

            # فایل راه‌انداز پایتون (اصلی)
            launcher_content = '''import os
import sys
import subprocess
import webbrowser
import time
from pathlib import Path

def print_step(step, message):
    """چاپ مرحله با فرمت زیبا"""
    print(f"\\n{'='*50}")
    print(f"📍 {step}: {message}")
    print(f"{'='*50}")

def run_command(command, success_msg, error_msg):
    """اجرای دستور و مدیریت خطا"""
    try:
        print(f"   🔧 اجرای دستور: {command}")
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=300)

        if result.returncode == 0:
            print(f"   ✅ {success_msg}")
            if result.stdout.strip():
                print(f"   📝 خروجی: {result.stdout.strip()}")
            return True
        else:
            print(f"   ❌ {error_msg}")
            if result.stderr.strip():
                print(f"   💥 خطا: {result.stderr.strip()}")
            return False
    except subprocess.TimeoutExpired:
        print(f"   ⏰ زمان اجرای دستور به پایان رسید: {command}")
        return False
    except Exception as e:
        print(f"   💥 خطای غیرمنتظره: {e}")
        return False

def check_python():
    """بررسی نصب پایتون"""
    print_step(1, "بررسی نصب پایتون")
    try:
        result = subprocess.run(["python", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"   ✅ پایتون پیدا شد: {result.stdout.strip()}")
            return True
        else:
            print("   ❌ پایتون پیدا نشد!")
            return False
    except:
        print("   ❌ پایتون پیدا نشد!")
        return False

def install_requirements():
    """نصب کتابخانه‌های مورد نیاز"""
    print_step(2, "نصب کتابخانه‌های مورد نیاز")

    commands = [
        ("python -m pip install --upgrade pip", "بروزرسانی pip", "خطا در بروزرسانی pip"),
        ("pip install -r requirements_offline.txt", "نصب کتابخانه‌ها از فایل requirements", "خطا در نصب کتابخانه‌ها")
    ]

    all_success = True
    for cmd, success_msg, error_msg in commands:
        if not run_command(cmd, success_msg, error_msg):
            all_success = False

    return all_success

def setup_database():
    """راه‌اندازی دیتابیس"""
    print_step(3, "راه‌اندازی دیتابیس")

    commands = [
        ("python manage.py migrate", "اجرای migrations", "خطا در اجرای migrations"),
        ("python manage.py shell -c \""
         "from django.contrib.auth import get_user_model; "
         "User = get_user_model(); "
         "if not User.objects.filter(username='admin').exists(): "
         "User.objects.create_superuser('admin', 'admin@plasco.com', 'admin123'); "
         "print('کاربر ادمین ایجاد شد: admin / admin123'); "
         "else: print('کاربر ادمین از قبل وجود دارد')\"", 
         "ایجاد کاربر ادمین", "خطا در ایجاد کاربر ادمین")
    ]

    all_success = True
    for cmd, success_msg, error_msg in commands:
        if not run_command(cmd, success_msg, error_msg):
            all_success = False

    return all_success

def start_server():
    """راه‌اندازی سرور"""
    print_step(4, "راه‌اندازی سرور")

    print("\\n🎉 سیستم آماده راه‌اندازی است!")
    print("\\n🌐 آدرس‌های دسترسی:")
    print("   📍 سیستم اصلی: http://localhost:8000")
    print("   🔧 پنل مدیریت: http://localhost:8000/admin")
    print("   👤 کاربر: admin")
    print("   🔑 رمز: admin123")
    print("\\n⏰ در حال راه‌اندازی سرور...")

    # باز کردن مرورگر
    try:
        time.sleep(2)
        webbrowser.open("http://localhost:8000")
        print("   🌐 مرورگر در حال باز شدن...")
    except:
        print("   ℹ️ امکان باز کردن خودکار مرورگر وجود ندارد")

    print("\\n⏹️ برای توقف سرور، کلیدهای Ctrl+C را فشار دهید")
    print("-" * 50)

    # راه‌اندازی سرور
    try:
        os.system("python manage.py runserver 0.0.0.0:8000")
    except KeyboardInterrupt:
        print("\\n⏹️ سرور متوقف شد")
    except Exception as e:
        print(f"💥 خطا در راه‌اندازی سرور: {e}")

def main():
    """تابع اصلی"""
    print("🚀 راه‌انداز خودکار سیستم پلاسکو")
    print("📅 ایجاد شده برای کاربران غیرفنی")
    print("=" * 60)

    # تغییر مسیر به پوشه فعلی
    os.chdir(Path(__file__).parent)

    try:
        # بررسی پایتون
        if not check_python():
            print("\\n❌ لطفا پایتون را از سایت python.org دانلود و نصب کنید")
            input("\\n📝 Enter برای خروج...")
            return

        # نصب requirements
        if not install_requirements():
            print("\\n⚠️ برخی کتابخانه‌ها با مشکل مواجه شدند، ادامه می‌دهیم...")

        # راه‌اندازی دیتابیس
        if not setup_database():
            print("\\n⚠️ خطا در راه‌اندازی دیتابیس، ادامه می‌دهیم...")

        # راه‌اندازی سرور
        start_server()

    except Exception as e:
        print(f"\\n💥 خطای غیرمنتظره: {e}")

    input("\\n📝 Enter برای بستن پنجره...")

if __name__ == "__main__":
    main()
'''
            zipf.writestr('plasco_launcher.py', launcher_content)

            # فایل BAT اصلی - بسیار ساده
            main_bat = '''@echo off
chcp 65001
title Plasco Auto Installer
echo.
echo ========================================
echo    Plasco Offline System - Auto Setup
echo ========================================
echo.
echo 🚀 Starting automatic installation...
echo 📝 This may take a few minutes...
echo.
echo Please wait...
python plasco_launcher.py
'''
            zipf.writestr('START_HERE.bat', main_bat)

            # فایل BAT جایگزین
            simple_bat = '''@echo off
chcp 65001
title Plasco Quick Start
echo.
echo Plasco Offline System
echo.
echo If you see errors, please:
echo 1. Install Python from python.org
echo 2. Run START_HERE.bat again
echo.
python plasco_launcher.py
pause
'''
            zipf.writestr('Run_Plasco.bat', simple_bat)

            # فایل راهنمای کامل
            readme_content = f'''
Plasco Offline System - Complete Installation
=============================================

📋 QUICK START (برای کاربران غیرفنی):
1. تمام فایل‌ها را در یک پوشه Extract کنید
2. فایل "START_HERE.bat" را اجرا کنید
3. منتظر بمانید تا سیستم به طور خودکار راه‌اندازی شود
4. مرورگر به طور خودکار باز می‌شود

🔧 DETAILED INSTRUCTIONS:

WHAT HAPPENS AUTOMATICALLY:
- ✅ بررسی نصب پایتون
- ✅ نصب خودکار کتابخانه‌ها
- ✅ ایجاد دیتابیس
- ✅ ایجاد کاربر ادمین
- ✅ راه‌اندازی سرور
- ✅ باز کردن مرورگر

🌐 ACCESS INFORMATION:
- سیستم اصلی: http://localhost:8000
- پنل مدیریت: http://localhost:8000/admin
- کاربر: admin
- رمز: admin123

📞 IF YOU HAVE PROBLEMS:
1. مطمئن شوید همه فایل‌ها Extract شده‌اند
2. فایل BAT را با راست کلیک → Run as Administrator اجرا کنید
3. اگر پایتون نصب نیست، از python.org دانلود کنید
4. با پشتیبانی تماس بگیرید

⚙️ TECHNICAL INFO:
- Python 3.8+ required
- IPهای مجاز: {', '.join(selected_ips)}
- Database: SQLite (db_offline.sqlite3)
- Port: 8000

📝 Created: {timezone.now().strftime("%Y/%m/%d %H:%M")}
'''
            zipf.writestr('README_FIRST.txt', readme_content)

            # فایل پیکربندی
            config_content = f'''[Plasco_Auto_Installer]
version=2.0
created={timezone.now().isoformat()}
allowed_ips={','.join(selected_ips)}
auto_install=true
admin_user=admin
admin_pass=admin123
'''
            zipf.writestr('config.ini', config_content)

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
            response['Content-Disposition'] = 'attachment; filename="plasco_auto_install.zip"'

            return response

        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'خطا در ایجاد فایل نصب: {str(e)}'
            })

    return JsonResponse({'status': 'error', 'message': 'متد غیرمجاز'})


