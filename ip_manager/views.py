from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from .models import AllowedIP
import json
import zipfile
import io
import os
from pathlib import Path
import shutil


# توابع مدیریت IPها
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
    """ایجاد پکیج نصب کامل - مشابه offline_ins اما با IPهای پویا"""
    try:
        BASE_DIR = Path(__file__).resolve().parent.parent.parent

        # ایجاد بافر ZIP در حافظه
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            print("📦 ایجاد پکیج نصب کامل...")

            # فایل‌های اصلی
            essential_files = [
                'manage.py',
                'requirements_offline.txt',
                'start_windows.bat',
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
                            # فقط فایل‌های پایتون، تمپلیت و استاتیک
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

            # ایجاد فایل settings_offline.py با IPهای انتخابی
            settings_content = f'''
"""
Django settings for plasco project.
برای اجرا روی کامپیوترهای داخلی شرکت - حالت آفلاین
ایجاد شده توسط سیستم مدیریت IP
IPهای مجاز: {', '.join(selected_ips)}
"""

from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

IS_OFFLINE_MODE = True
SECRET_KEY = 'django-insecure-9a=faq-)zl&%@!5(9t8!0r(ar)&()3l+hc#a)+-!eh$-ljkdh@'
DEBUG = True

ALLOWED_HOSTS = {selected_ips}

print("🟢 اجرا در حالت آفلاین - ديتابيس محلي (Slave)")
print("🔐 IPهای مجاز: {', '.join(selected_ips)}")

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
    'offline_ins',
    'ip_manager',
    'home_app'
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
OFFLINE_MODE = True

# تنظیمات REST Framework
REST_FRAMEWORK = {{
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ]
}}

# تنظیمات CORS
CORS_ALLOWED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
] + [f"http://{ip}:8000" for ip in selected_ips]

CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True
'''

            zipf.writestr('plasco/settings_offline.py', settings_content.strip())
            print("✅ فایل settings_offline.py با IPهای انتخابی ایجاد شد")

            # ایجاد فایل start_windows.bat
            bat_content = f'''@echo off
chcp 65001
echo 🟢 در حال راه‌اندازی سیستم آفلاین پلاسکو...
echo.
echo 📅 ایجاد شده در: {timezone.now().strftime("%Y/%m/%d %H:%M")}
echo 🔐 IPهای مجاز: {', '.join(selected_ips)}
echo.

# بررسی وجود Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python نصب نیست. لطفا Python 3.8+ را نصب کنید.
    echo از آدرس: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo ✅ Python تشخیص داده شد
echo.

# نصب requirements
echo 📦 در حال نصب کتابخانه‌های مورد نیاز...
pip install -r requirements_offline.txt

if %errorlevel% neq 0 (
    echo ⚠️ خطا در نصب کتابخانه‌ها
    echo 🔧 در حال تلاش مجدد با upgrade pip...
    python -m pip install --upgrade pip
    pip install -r requirements_offline.txt
)

echo.
echo 🗃️ در حال ایجاد دیتابیس و اجرای migrations...
python manage.py migrate --settings=plasco.settings_offline

echo.
echo 🚀 در حال راه‌اندازی سرور آفلاین...
echo 🔗 آدرس‌های دسترسی:
echo    http://localhost:8000
echo    http://127.0.0.1:8000
'''

            for ip in selected_ips:
                bat_content += f'echo    http://{ip}:8000\n'

            bat_content += f'''echo.
echo ⏰ لطفا منتظر بمانید...
echo.

# اجرای سرور
python manage.py runserver 0.0.0.0:8000 --settings=plasco.settings_offline

echo.
echo ⚠️ سرور متوقف شد
pause
'''

            zipf.writestr('start_windows.bat', bat_content)
            print("✅ فایل start_windows.bat ایجاد شد")

            # ایجاد فایل requirements_offline.txt
            requirements_content = '''Django==4.2.7
django-cors-headers==4.3.1
djangorestframework==3.14.0
Pillow==10.0.1
requests==2.31.0
mysqlclient==2.1.1
'''
            zipf.writestr('requirements_offline.txt', requirements_content)
            print("✅ فایل requirements_offline.txt ایجاد شد")

            # فایل README
            readme_content = f'''
Plasco Offline Installer - نسخه کامل
=====================================

📅 ایجاد شده در: {timezone.now().strftime("%Y/%m/%d %H:%M")}
🔐 IPهای مجاز: {', '.join(selected_ips)}

📋 دستورالعمل نصب:

1. تمام فایل‌ها را در یک پوشه Extract کنید
2. فایل start_windows.bat را اجرا کنید
3. سیستم به صورت خودکار راه‌اندازی می‌شود
4. به آدرس‌های زیر دسترسی داشته باشید:

   http://localhost:8000
   http://127.0.0.1:8000
'''

            for ip in selected_ips:
                readme_content += f'   http://{ip}:8000\n'

            readme_content += '''

⚙️ نیازمندی‌ها:
- Python 3.8 یا بالاتر
- دسترسی به اینترنت برای نصب اولیه کتابخانه‌ها

🛠️ ویژگی‌ها:
- سیستم کامل پلاسکو با تمام ماژول‌ها
- دیتابیس SQLite محلی
- تنظیمات خودکار
- پشتیبانی از IPهای انتخابی

📞 پشتیبانی:
در صورت بروز مشکل با واحد فناوری اطلاعات تماس بگیرید.
'''

            zipf.writestr('README.txt', readme_content.strip())
            print("✅ فایل README.txt ایجاد شد")

        print("✅ پکیج نصب کامل ایجاد شد")
        return zip_buffer

    except Exception as e:
        print(f"❌ خطا در ایجاد پکیج کامل: {str(e)}")
        import traceback
        print(f"❌ جزئیات خطا: {traceback.format_exc()}")
        return None


@csrf_exempt
def create_offline_installer(request):
    """ایجاد و دانلود مستقیم فایل نصب کامل"""
    print("🎯 درخواست ایجاد فایل نصب کامل دریافت شد")

    if request.method == 'POST':
        try:
            # دریافت IPهای انتخاب شده
            selected_ips_json = request.POST.get('selected_ips', '[]')
            selected_ips = json.loads(selected_ips_json)

            print(f"🔢 IPهای دریافت شده: {selected_ips}")

            if not selected_ips:
                return JsonResponse({
                    'status': 'error',
                    'message': 'هیچ IPی انتخاب نشده است'
                })

            # ایجاد پکیج نصب کامل
            zip_buffer = create_complete_install_package(selected_ips)

            if not zip_buffer:
                return JsonResponse({
                    'status': 'error',
                    'message': 'خطا در ایجاد فایل نصب'
                })

            # برگرداندن فایل به عنوان response
            zip_buffer.seek(0)
            response = HttpResponse(
                zip_buffer.getvalue(),
                content_type='application/zip'
            )
            response[
                'Content-Disposition'] = f'attachment; filename="plasco_complete_offline_{int(timezone.now().timestamp())}.zip"'

            file_size = len(zip_buffer.getvalue())
            print(f"🚀 فایل کامل برای دانلود ارسال شد - حجم: {file_size} بایت")

            return response

        except Exception as e:
            print(f"❌ خطا در ایجاد فایل: {str(e)}")
            import traceback
            print(f"❌ جزئیات خطا: {traceback.format_exc()}")

            return JsonResponse({
                'status': 'error',
                'message': f'خطا در ایجاد فایل نصب: {str(e)}'
            })

    return JsonResponse({'status': 'error', 'message': 'لطفاً از POST استفاده کنید'})