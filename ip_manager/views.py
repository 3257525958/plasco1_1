# from django.shortcuts import render, get_object_or_404
# from django.http import JsonResponse
# from django.views.decorators.csrf import csrf_exempt
# from django.utils import timezone
# from .models import AllowedIP
# import json
#
#
# def manage_ips(request):
#     """صفحه مدیریت IPها"""
#     return render(request, 'ip_manager/manage_ips.html')
#
#
# @csrf_exempt
# def list_ips(request):
#     """دریافت لیست IPها (API)"""
#     try:
#         ips = AllowedIP.objects.all().order_by('-created_at')
#         ip_list = []
#
#         for ip in ips:
#             ip_list.append({
#                 'id': ip.id,
#                 'ip_address': ip.ip_address,
#                 'description': ip.description,
#                 'is_active': ip.is_active,
#                 'created_at': ip.created_at.strftime('%Y/%m/%d %H:%M')
#             })
#
#         return JsonResponse({'status': 'success', 'ips': ip_list})
#     except Exception as e:
#         return JsonResponse({'status': 'error', 'message': str(e)})
#
#
# @csrf_exempt
# def add_ip(request):
#     """افزودن IP جدید (API)"""
#     if request.method == 'POST':
#         try:
#             ip_address = request.POST.get('ip_address')
#             description = request.POST.get('description', '')
#
#             # اعتبارسنجی IP
#             if not ip_address:
#                 return JsonResponse({'status': 'error', 'message': 'آدرس IP الزامی است'})
#
#             # بررسی تکراری نبودن IP
#             if AllowedIP.objects.filter(ip_address=ip_address).exists():
#                 return JsonResponse({'status': 'error', 'message': 'این IP قبلاً ثبت شده است'})
#
#             # ایجاد IP جدید
#             allowed_ip = AllowedIP.objects.create(
#                 ip_address=ip_address,
#                 description=description
#             )
#
#             return JsonResponse({
#                 'status': 'success',
#                 'message': 'IP با موفقیت اضافه شد',
#                 'id': allowed_ip.id
#             })
#
#         except Exception as e:
#             return JsonResponse({'status': 'error', 'message': f'خطا در افزودن IP: {str(e)}'})
#     else:
#         return JsonResponse({'status': 'error', 'message': 'متد غیرمجاز'})
#
#
# @csrf_exempt
# def delete_ip(request, ip_id):
#     """حذف IP (API)"""
#     try:
#         ip = get_object_or_404(AllowedIP, id=ip_id)
#         ip.delete()
#         return JsonResponse({'status': 'success', 'message': 'IP با موفقیت حذف شد'})
#     except Exception as e:
#         return JsonResponse({'status': 'error', 'message': f'خطا در حذف IP: {str(e)}'})
#
#
# @csrf_exempt
# def update_ip(request, ip_id):
#     """ویرایش IP (API)"""
#     if request.method == 'POST':
#         try:
#             ip = get_object_or_404(AllowedIP, id=ip_id)
#             ip_address = request.POST.get('ip_address')
#             description = request.POST.get('description', '')
#
#             # بررسی تکراری نبودن IP (به جز خودش)
#             if AllowedIP.objects.filter(ip_address=ip_address).exclude(id=ip_id).exists():
#                 return JsonResponse({'status': 'error', 'message': 'این IP قبلاً ثبت شده است'})
#
#             ip.ip_address = ip_address
#             ip.description = description
#             ip.save()
#
#             return JsonResponse({'status': 'success', 'message': 'IP با موفقیت ویرایش شد'})
#         except Exception as e:
#             return JsonResponse({'status': 'error', 'message': f'خطا در ویرایش IP: {str(e)}'})
#     else:
#         return JsonResponse({'status': 'error', 'message': 'متد غیرمجاز'})
#
# @csrf_exempt
# def toggle_ip(request, ip_id):
#     """فعال/غیرفعال کردن IP (API)"""
#     if request.method == 'POST':
#         try:
#             ip = get_object_or_404(AllowedIP, id=ip_id)
#             action = request.POST.get('action')
#
#             if action == 'activate':
#                 ip.is_active = True
#                 message = 'IP با موفقیت فعال شد'
#             elif action == 'deactivate':
#                 ip.is_active = False
#                 message = 'IP با موفقیت غیرفعال شد'
#             else:
#                 return JsonResponse({'status': 'error', 'message': 'عمل نامعتبر'})
#
#             ip.save()
#             return JsonResponse({'status': 'success', 'message': message})
#         except Exception as e:
#             return JsonResponse({'status': 'error', 'message': f'خطا در تغییر وضعیت IP: {str(e)}'})
#     else:
#         return JsonResponse({'status': 'error', 'message': 'متد غیرمجاز'})
#
#
# # در ip_manager/views.py این تابع را اضافه کنید
#
#
# # @csrf_exempt
# # def create_offline_installer(request):
# #     """ایجاد فایل نصب آفلاین با IPهای انتخاب شده"""
# #     if request.method == 'POST':
# #         try:
# #             import json
# #             from pathlib import Path
# #             import os
# #             import zipfile
# #             import shutil
# #             from django.utils import timezone
# #
# #             print("🔹 مرحله 1: شروع ایجاد فایل نصب آفلاین")
# #
# #             # دریافت IPهای انتخاب شده
# #             selected_ips_json = request.POST.get('selected_ips', '[]')
# #             selected_ips = json.loads(selected_ips_json)
# #
# #             print(f"🔹 مرحله 2: دریافت {len(selected_ips)} IP: {selected_ips}")
# #
# #             BASE_DIR = Path(__file__).resolve().parent.parent.parent
# #             print(f"🔹 مرحله 3: مسیر BASE_DIR: {BASE_DIR}")
# #
# #             # ایجاد فایل settings_offline.py با IPهای انتخاب شده
# #             print("🔹 مرحله 4: ایجاد محتوای فایل settings_offline.py")
# #             settings_content = f'''
# # """
# # Django settings for plasco project.
# # برای اجرا روی کامپیوترهای داخلی شرکت - حالت آفلاین
# # ساخته شده در: {timezone.now().strftime("%Y/%m/%d %H:%M")}
# # IPهای مجاز: {', '.join(selected_ips)}
# # """
# #
# # from pathlib import Path
# # import os
# #
# # BASE_DIR = Path(__file__).resolve().parent.parent
# #
# # IS_OFFLINE_MODE = True
# # SECRET_KEY = 'django-insecure-offline-{int(timezone.now().timestamp())}'
# # DEBUG = True
# #
# # ALLOWED_HOSTS = {selected_ips}
# #
# # print("🟢 اجرا در حالت آفلاین - ديتابيس محلي (Slave)")
# # print("🔐 IPهای مجاز: {', '.join(selected_ips)}")
# #
# # INSTALLED_APPS = [
# #     'django.contrib.admin',
# #     'django.contrib.auth',
# #     'django.contrib.contenttypes',
# #     'django.contrib.sessions',
# #     'django.contrib.messages',
# #     'django.contrib.staticfiles',
# #     'rest_framework',
# #     'rest_framework.authtoken',
# #     'corsheaders',
# #     'account_app',
# #     'dashbord_app',
# #     'cantact_app',
# #     'invoice_app',
# #     'it_app',
# #     'pos_payment',
# #     'sync_app',
# #     'sync_api',
# #     'control_panel',
# #     'offline_ins',
# #     'ip_manager'
# # ]
# #
# # MIDDLEWARE = [
# #     'django.middleware.security.SecurityMiddleware',
# #     'django.contrib.sessions.middleware.SessionMiddleware',
# #     'django.middleware.common.CommonMiddleware',
# #     'django.middleware.csrf.CsrfViewMiddleware',
# #     'django.contrib.auth.middleware.AuthenticationMiddleware',
# #     'django.contrib.messages.middleware.MessageMiddleware',
# #     'django.middleware.clickjacking.XFrameOptionsMiddleware',
# #     'corsheaders.middleware.CorsMiddleware',
# # ]
# #
# # ROOT_URLCONF = 'plasco.urls'
# #
# # TEMPLATES = [
# #     {{
# #         'BACKEND': 'django.template.backends.django.DjangoTemplates',
# #         'DIRS': [BASE_DIR / 'templates'],
# #         'APP_DIRS': True,
# #         'OPTIONS': {{
# #             'context_processors': [
# #                 'django.template.context_processors.request',
# #                 'django.contrib.auth.context_processors.auth',
# #                 'django.contrib.messages.context_processors.messages',
# #             ],
# #         }},
# #     }},
# # ]
# #
# # WSGI_APPLICATION = 'plasco.wsgi.application'
# #
# # DATABASES = {{
# #     'default': {{
# #         'ENGINE': 'django.db.backends.sqlite3',
# #         'NAME': BASE_DIR / 'db_offline.sqlite3',
# #     }}
# # }}
# #
# # AUTH_PASSWORD_VALIDATORS = [
# #     {{
# #         'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
# #     }},
# #     {{
# #         'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
# #     }},
# #     {{
# #         'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
# #     }},
# #     {{
# #         'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
# #     }},
# # ]
# #
# # LANGUAGE_CODE = 'fa-ir'
# # TIME_ZONE = 'Asia/Tehran'
# # USE_I18N = True
# # USE_TZ = True
# #
# # STATIC_URL = '/static/'
# # MEDIA_URL = '/media/'
# # STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
# # STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
# # MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
# #
# # DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
# # OFFLINE_MODE = True
# #
# # # غیرفعال کردن سیگنال‌های سینک در حالت آفلاین
# # SYNC_DISABLED = True
# # '''
# #
# #             # ایجاد فایل start_windows.bat
# #             print("🔹 مرحله 5: ایجاد فایل start_windows.bat")
# #             bat_content = f'''@echo off
# # chcp 65001
# # echo.
# # echo 🟢 در حال راه‌اندازی سیستم آفلاین پلاسکو...
# # echo 📅 تاریخ ایجاد: {timezone.now().strftime("%Y/%m/%d")}
# # echo 🔐 IPهای مجاز: {', '.join(selected_ips)}
# # echo.
# #
# # REM بررسی وجود Python
# # python --version >nul 2>&1
# # if %errorlevel% neq 0 (
# #     echo ❌ Python نصب نیست. لطفا Python 3.8+ را نصب کنید.
# #     echo از آدرس: https://www.python.org/downloads/
# #     pause
# #     exit /b 1
# # )
# #
# # echo ✅ Python تشخیص داده شد
# # echo.
# #
# # REM نصب requirements
# # echo 📦 در حال نصب کتابخانه‌های مورد نیاز...
# # pip install -r requirements_offline.txt
# #
# # echo.
# # echo 🚀 در حال راه‌اندازی سرور آفلاین...
# # echo 🔗 آدرس دسترسی: http://localhost:8000
# # echo 🔐 IPهای مجاز: {', '.join(selected_ips)}
# # echo.
# #
# # REM اجرای سرور
# # python manage.py runserver 0.0.0.0:8000 --settings=plasco.settings_offline
# #
# # pause
# # '''
# #
# #             # ایجاد فایل requirements_offline.txt
# #             print("🔹 مرحله 6: ایجاد فایل requirements_offline.txt")
# #             requirements_content = '''Django==5.2.4
# # django-cors-headers==4.4.0
# # djangorestframework==3.15.2
# # mysqlclient==2.2.4
# # Pillow==10.3.0
# # requests==2.31.0
# # '''
# #
# #             # ایجاد پوشه خروجی
# #             print("🔹 مرحله 7: ایجاد پوشه خروجی")
# #             output_dir = BASE_DIR / 'media' / 'offline_installers'
# #             output_dir.mkdir(parents=True, exist_ok=True)
# #             print(f"✅ پوشه خروجی ایجاد شد: {output_dir}")
# #
# #             # نام فایل با timestamp
# #             timestamp = int(timezone.now().timestamp())
# #             zip_filename = f'plasco_offline_installer_{timestamp}.zip'
# #             zip_path = output_dir / zip_filename
# #
# #             print("🔹 مرحله 8: شروع ایجاد فایل ZIP...")
# #
# #             # ایجاد فایل ZIP
# #             with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
# #                 # اضافه کردن فایل‌های اصلی
# #                 print("🔹 مرحله 9: اضافه کردن فایل‌های اصلی")
# #                 essential_files = {
# #                     'manage.py': BASE_DIR / 'manage.py',
# #                     'plasco/__init__.py': BASE_DIR / 'plasco' / '__init__.py',
# #                     'plasco/urls.py': BASE_DIR / 'plasco' / 'urls.py',
# #                     'plasco/wsgi.py': BASE_DIR / 'plasco' / 'wsgi.py'
# #                 }
# #
# #                 for arcname, filepath in essential_files.items():
# #                     if filepath.exists():
# #                         zipf.write(filepath, arcname)
# #                         print(f"✅ اضافه شد: {arcname}")
# #                     else:
# #                         print(f"⚠️ فایل یافت نشد: {filepath}")
# #
# #                 # اضافه کردن فایل‌های ایجاد شده
# #                 print("🔹 مرحله 10: اضافه کردن فایل‌های ایجاد شده")
# #                 zipf.writestr('plasco/settings_offline.py', settings_content)
# #                 zipf.writestr('start_windows.bat', bat_content)
# #                 zipf.writestr('requirements_offline.txt', requirements_content)
# #
# #                 print("✅ فایل‌های تنظیمات اضافه شدند")
# #
# #                 # اضافه کردن پوشه اپ‌ها
# #                 print("🔹 مرحله 11: اضافه کردن پوشه اپ‌ها")
# #                 app_folders = [
# #                     'account_app', 'dashbord_app', 'cantact_app', 'invoice_app',
# #                     'it_app', 'pos_payment', 'sync_app', 'sync_api',
# #                     'control_panel', 'offline_ins', 'ip_manager', 'home_app'
# #                 ]
# #
# #                 for app in app_folders:
# #                     app_path = BASE_DIR / app
# #                     if app_path.exists():
# #                         file_count = 0
# #                         for root, dirs, files in os.walk(app_path):
# #                             for file in files:
# #                                 if file.endswith('.py') or file.endswith('.html') or file in ['apps.py', 'models.py',
# #                                                                                               'views.py', 'urls.py']:
# #                                     file_path = os.path.join(root, file)
# #                                     arcname = os.path.relpath(file_path, BASE_DIR)
# #                                     zipf.write(file_path, arcname)
# #                                     file_count += 1
# #                         print(f"✅ اپ {app} اضافه شد ({file_count} فایل)")
# #                     else:
# #                         print(f"⚠️ پوشه اپ یافت نشد: {app_path}")
# #
# #                 # اضافه کردن پوشه templates
# #                 print("🔹 مرحله 12: اضافه کردن پوشه templates")
# #                 templates_path = BASE_DIR / 'templates'
# #                 if templates_path.exists():
# #                     template_count = 0
# #                     for root, dirs, files in os.walk(templates_path):
# #                         for file in files:
# #                             file_path = os.path.join(root, file)
# #                             arcname = os.path.relpath(file_path, BASE_DIR)
# #                             zipf.write(file_path, arcname)
# #                             template_count += 1
# #                     print(f"✅ پوشه templates اضافه شد ({template_count} فایل)")
# #                 else:
# #                     print("⚠️ پوشه templates یافت نشد")
# #
# #             print(f"✅ فایل نصب ایجاد شد: {zip_path}")
# #             print(f"📦 سایز فایل: {zip_path.stat().st_size} بایت")
# #
# #             download_url = f'/media/offline_installers/{zip_filename}'
# #             print(f"🔗 لینک دانلود: {download_url}")
# #
# #             return JsonResponse({
# #                 'status': 'success',
# #                 'message': f'فایل نصب با {len(selected_ips)} IP ایجاد شد',
# #                 'download_url': download_url,
# #                 'file_size': zip_path.stat().st_size,
# #                 'selected_ips': selected_ips
# #             })
# #
# #         except Exception as e:
# #             import traceback
# #             error_details = traceback.format_exc()
# #             print(f"❌ خطا در ایجاد فایل نصب: {str(e)}")
# #             print(f"❌ جزئیات خطا: {error_details}")
# #
# #             return JsonResponse({
# #                 'status': 'error',
# #                 'message': f'خطا در ایجاد فایل نصب: {str(e)}'
# #             })
# #
# #     return JsonResponse({'status': 'error', 'message': 'متد غیرمجاز'})
# from django.shortcuts import render, get_object_or_404
# from django.http import JsonResponse  # ✅ این خط را اضافه کنید
# from django.views.decorators.csrf import csrf_exempt
# from django.utils import timezone
# from .models import AllowedIP
# import json
#
# # بقیه کدها بدون تغییر...
# @csrf_exempt
# def create_offline_installer(request):
#     """ایجاد فایل نصب آفلاین با IPهای انتخاب شده - نسخه ساده برای تست"""
#     print("🔹 درخواست ایجاد فایل نصب دریافت شد")
#
#     if request.method == 'POST':
#         try:
#             import json
#             from django.http import JsonResponse
#             from django.utils import timezone
#
#             # دریافت IPهای انتخاب شده
#             selected_ips_json = request.POST.get('selected_ips', '[]')
#             selected_ips = json.loads(selected_ips_json)
#
#             print(f"🔹 IPهای دریافت شده: {selected_ips}")
#
#             # ایجاد یک پاسخ تستی ساده
#             response_data = {
#                 'status': 'success',
#                 'message': f'فایل نصب با {len(selected_ips)} IP ایجاد شد (نسخه تست)',
#                 'download_url': '/media/test_download.zip',
#                 'selected_ips': selected_ips
#             }
#
#             print("✅ پاسخ ارسال می‌شود:", response_data)
#             return JsonResponse(response_data)
#
#         except Exception as e:
#             print(f"❌ خطا در ایجاد فایل نصب: {str(e)}")
#             return JsonResponse({
#                 'status': 'error',
#                 'message': f'خطا در ایجاد فایل نصب: {str(e)}'
#             })
#
#     print("❌ متد غیرمجاز")
#     return JsonResponse({'status': 'error', 'message': 'متد غیرمجاز'})
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from .models import AllowedIP
import json
import os
import zipfile
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

            # اعتبارسنجی IP
            if not ip_address:
                return JsonResponse({'status': 'error', 'message': 'آدرس IP الزامی است'})

            # بررسی تکراری نبودن IP
            if AllowedIP.objects.filter(ip_address=ip_address).exists():
                return JsonResponse({'status': 'error', 'message': 'این IP قبلاً ثبت شده است'})

            # ایجاد IP جدید
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

            # بررسی تکراری نبودن IP (به جز خودش)
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


from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json


@csrf_exempt
def create_offline_installer(request):
    """ساده‌ترین نسخه برای تست"""
    print("🎯 درخواست POST دریافت شد!")

    if request.method == 'POST':
        try:
            print("📦 داده‌های POST:", request.POST)

            selected_ips_json = request.POST.get('selected_ips', '[]')
            selected_ips = json.loads(selected_ips_json)

            print(f"🔢 IPهای دریافت شده: {selected_ips}")

            # پاسخ ساده و موفق
            return JsonResponse({
                'status': 'success',
                'message': f'فایل نصب برای {len(selected_ips)} IP ایجاد شد!',
                'download_url': '/media/test_file.zip',
                'selected_ips': selected_ips
            })

        except Exception as e:
            print(f"❌ خطا: {e}")
            return JsonResponse({
                'status': 'error',
                'message': f'خطا: {str(e)}'
            })

    return JsonResponse({'status': 'error', 'message': 'متد غیرمجاز'})