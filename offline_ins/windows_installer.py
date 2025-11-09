import os
import zipfile
from pathlib import Path


def create_windows_installer():
    """ایجاد بسته نصب ویندوز"""

    # محتوای فایل start_windows.bat
    bat_content = '''@echo off
chcp 65001
echo 🟢 در حال راه‌اندازی سیستم آفلاین پلاسکو...
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

echo.
echo 🚀 در حال راه‌اندازی سرور آفلاین...
echo 🔗 آدرس دسترسی: http://192.168.1.172:8000
echo.

# اجرای سرور
python manage.py runserver 192.168.1.172:8000 --settings=plasco.settings_offline

pause
'''

    # محتوای فایل requirements_offline.txt
    requirements_content = '''Django==5.2.4
django-cors-headers==4.4.0
djangorestframework==3.15.2
mysqlclient==2.2.4
Pillow==10.3.0
requests==2.31.0
'''

    return bat_content, requirements_content


def create_install_package():
    """ایجاد پکیج نصب"""
    BASE_DIR = Path(__file__).resolve().parent.parent

    # ایجاد پکیج
    package_path = BASE_DIR / 'offline_install_package.zip'

    with zipfile.ZipFile(package_path, 'w') as zipf:
        # اضافه کردن فایل‌های ضروری
        essential_files = [
            'manage.py',
            'plasco/__init__.py',
            'plasco/urls.py',
            'plasco/wsgi.py',
            'requirements_offline.txt',
            'start_windows.bat'
        ]

        for file in essential_files:
            file_path = BASE_DIR / file
            if file_path.exists():
                zipf.write(file_path, file)

    return package_path