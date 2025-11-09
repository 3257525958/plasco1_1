from django.shortcuts import render, redirect
from .windows_installer import create_windows_installer, create_install_package
import zipfile
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import os
import subprocess
import sqlite3
from pathlib import Path
import shutil
from django.conf import settings
from plasco.offline_ip_manager import is_allowed_offline_ip, get_client_ip, add_allowed_ip
import logging
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import os
import subprocess
import sqlite3
from pathlib import Path
import shutil
from django.conf import settings
from plasco.offline_ip_manager import is_allowed_offline_ip, get_client_ip, add_allowed_ip

# این خط باید حتماً وجود داشته باشد
logger = logging.getLogger(__name__)



def create_install_package():
    """ایجاد پکیج نصب کامل"""
    try:
        BASE_DIR = Path(__file__).resolve().parent.parent

        print("📦 ایجاد پکیج نصب کامل...")

        # ایجاد فایل ZIP
        import zipfile
        import os

        package_path = BASE_DIR / 'plasco_offline_package.zip'

        with zipfile.ZipFile(package_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # فایل‌های اصلی
            essential_files = [
                'manage.py',
                'requirements_offline.txt',
                'start_windows.bat',
                'plasco/settings_offline.py',
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
                'control_panel', 'offline_ins', 'home_app'
            ]

            for app in app_folders:
                app_path = BASE_DIR / app
                if app_path.exists():
                    for root, dirs, files in os.walk(app_path):
                        for file in files:
                            if file.endswith('.py'):
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

        print(f"✅ پکیج نصب ایجاد شد: {package_path}")
        return str(package_path)

    except Exception as e:
        print(f"❌ خطا در ایجاد پکیج: {str(e)}")
        return None


def offline_install(request):
    """صفحه نصب آفلاین"""
    if not is_allowed_offline_ip(request):
        return redirect('/')

    context = {
        'client_ip': get_client_ip(request),
        'installation_steps': [
            'بررسی سیستم',
            'افزودن IP به لیست مجاز',
            'ایجاد دیتابیس SQLite',
            'پیکربندی تنظیمات آفلاین',
            'اتمام نصب'
        ]
    }
    return render(request, 'offline_ins/install.html', context)


@csrf_exempt
def install_step(request):
    """اجرای مرحله به مرحله نصب"""
    if not is_allowed_offline_ip(request):
        return JsonResponse({'status': 'error', 'message': 'دسترسی غیرمجاز'})

    step = request.POST.get('step', '1')
    client_ip = get_client_ip(request)

    try:
        if step == '1':
            # مرحله 1: بررسی سیستم
            return check_system()

        elif step == '2':
            # مرحله 2: افزودن IP به لیست مجاز
            return add_ip_to_allowed(client_ip)

        elif step == '3':
            # مرحله 3: ایجاد دیتابیس SQLite
            return create_offline_database()

        elif step == '4':
            # مرحله 4: پیکربندی تنظیمات آفلاین
            return setup_offline_settings()

        elif step == '5':
            # مرحله 5: اتمام نصب
            return finish_installation(request)

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'خطا در مرحله نصب: {str(e)}'
        })


def check_system():
    """بررسی سیستم"""
    # بررسی وجود پوشه‌های لازم
    required_dirs = ['static', 'media', 'templates']
    for dir_name in required_dirs:
        dir_path = Path(__file__).resolve().parent.parent.parent / dir_name
        if not dir_path.exists():
            os.makedirs(dir_path)

    return JsonResponse({
        'status': 'success',
        'message': 'سیستم بررسی شد و آماده نصب است',
        'next_step': '2'
    })


def add_ip_to_allowed(client_ip):
    """افزودن IP به لیست مجاز"""
    add_allowed_ip(client_ip)

    return JsonResponse({
        'status': 'success',
        'message': f'IP {client_ip} به لیست مجاز اضافه شد',
        'next_step': '3'
    })


def create_offline_database():
    """ایجاد دیتابیس SQLite"""
    try:
        BASE_DIR = Path(__file__).resolve().parent.parent
        db_path = BASE_DIR / 'db_offline.sqlite3'

        # اگر دیتابیس قدیمی وجود دارد، پاک شود
        if db_path.exists():
            os.remove(db_path)

        # ایجاد دیتابیس جدید
        conn = sqlite3.connect(db_path)
        conn.close()

        # اجرای migrations برای ایجاد جداول
        try:
            subprocess.run([
                'python', 'manage.py', 'migrate',
                '--settings=plasco.settings_offline'
            ], capture_output=True, text=True, timeout=60)
        except:
            pass  # اگر اجرا نشد، بعداً دستی انجام می‌شود

        return JsonResponse({
            'status': 'success',
            'message': 'دیتابیس آفلاین ایجاد شد',
            'next_step': '4'
        })

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'خطا در ایجاد دیتابیس: {str(e)}'
        })


def setup_offline_settings():
    """ایجاد بسته نصب ویندوز"""
    try:
        BASE_DIR = Path(__file__).resolve().parent.parent

        print("🔧 ایجاد بسته نصب ویندوز...")

        # ایجاد فایل‌های نصب ویندوز
        bat_content, requirements_content = create_windows_installer()

        # ذخیره فایل start_windows.bat
        bat_path = BASE_DIR / 'start_windows.bat'
        with open(bat_path, 'w', encoding='utf-8') as f:
            f.write(bat_content)

        # ذخیره فایل requirements
        requirements_path = BASE_DIR / 'requirements_offline.txt'
        with open(requirements_path, 'w', encoding='utf-8') as f:
            f.write(requirements_content)

        # ایجاد فایل settings_offline.py
        settings_offline_path = BASE_DIR / 'plasco' / 'settings_offline.py'
        settings_content = '''
"""
Django settings for plasco project.
برای اجرا روی کامپیوترهای داخلی شرکت - حالت آفلاین
"""

from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

IS_OFFLINE_MODE = True
SECRET_KEY = 'django-insecure-9a=faq-)zl&%@!5(9t8!0r(ar)&()3l+hc#a)+-!eh$-ljkdh@'
DEBUG = True

ALLOWED_HOSTS = ['192.168.1.172', '192.168.1.157', '127.0.0.1', 'localhost', '192.168.1.100', '192.168.1.101']

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
    'account_app',
    'dashbord_app',
    'cantact_app',
    'invoice_app',
    'it_app',
    'pos_payment',
    'sync_app',
    'sync_api',
    'control_panel',
    'offline_ins'
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
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'plasco.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db_offline.sqlite3',
    }
}

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
OFFLINE_MODE = True
'''

        with open(settings_offline_path, 'w', encoding='utf-8') as f:
            f.write(settings_content)

        print("✅ بسته نصب ویندوز ایجاد شد")

        return JsonResponse({
            'status': 'success',
            'message': 'بسته نصب ویندوز ایجاد شد. آماده دانلود...',
            'next_step': '5'
        })

    except Exception as e:
        print(f"❌ خطا در ایجاد بسته نصب: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': f'خطا در ایجاد بسته نصب: {str(e)}'
        })


def finish_installation(request):
    """اتمام نصب و ایجاد پکیج دانلود"""
    try:
        # ایجاد پکیج نصب
        package_path = create_install_package()

        if package_path:
            # ایجاد لینک دانلود
            download_url = f"/media/offline_package/plasco_offline_package.zip"

            # کپی پکیج به پوشه media برای دانلود
            import shutil
            media_dir = Path(__file__).resolve().parent.parent / 'media' / 'offline_package'
            media_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(package_path, media_dir / 'plasco_offline_package.zip')

            return JsonResponse({
                'status': 'success',
                'message': 'نصب کامل شد! حالا می‌توانید بسته نصب را دانلود کنید.',
                'download_url': download_url,
                'redirect': '/offline/success/'
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'خطا در ایجاد بسته نصب'
            })

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'خطا در اتمام نصب: {str(e)}'
        })


def offline_success(request):
    """صفحه موفقیت نصب"""
    return render(request, 'offline_ins/success.html', {
        'client_ip': get_client_ip(request)
    })


def switch_to_offline(request):
    """سوئیچ به حالت آفلاین"""
    # تنظیم session برای حالت آفلاین
    request.session['operation_mode'] = 'offline'
    request.session['offline_installed'] = True

    # هدایت به صفحه اصلی سیستم آفلاین
    return redirect('/')

