import os
import sys
import subprocess
import socket
import requests
import time
import json
import shutil
from pathlib import Path


class OfflineInstaller:
    def __init__(self, client_ip, server_url):
        self.client_ip = client_ip
        self.server_url = server_url
        self.base_dir = Path(__file__).parent
        self.install_log = self.base_dir / 'install_log.txt'
        self.progress_file = self.base_dir / 'install_progress.json'

    def log(self, message):
        print(f"[{time.ctime()}] {message}")
        with open(self.install_log, 'a', encoding='utf-8') as f:
            f.write(f"{time.ctime()}: {message}\n")

    def update_progress(self, step, message, status='running'):
        progress_data = {
            'step': step,
            'message': message,
            'status': status,
            'timestamp': time.time(),
            'client_ip': self.client_ip
        }

        with open(self.progress_file, 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, ensure_ascii=False)

    def run_management_command(self, command):
        """اجرای دستور مدیریتی Django"""
        try:
            self.log(f"اجرای دستور: {command}")
            result = subprocess.run(
                ['python', 'manage.py'] + command.split(),
                cwd=self.base_dir,
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=300
            )

            if result.returncode == 0:
                self.log(f"✅ دستور موفق: {command}")
                return True
            else:
                self.log(f"❌ خطا در دستور {command}: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            self.log(f"⏰ timeout در دستور: {command}")
            return False
        except Exception as e:
            self.log(f"❌ خطا در اجرای دستور {command}: {e}")
            return False

    def step1_check_installation(self):
        """مرحله 1: بررسی نصب قبلی"""
        self.update_progress(1, 'بررسی نصب قبلی')
        self.log("🔍 در حال بررسی نصب قبلی...")

        # بررسی وجود دیتابیس آفلاین
        db_file = self.base_dir / 'db_offline.sqlite3'
        if db_file.exists():
            self.log("⚠️ دیتابیس آفلاین از قبل وجود دارد")
            return False
        else:
            self.log("✅ سیستم قبلاً نصب نشده است")
            return True

    def step2_install_system(self):
        """مرحله 2: نصب سیستم آفلاین"""
        self.update_progress(2, 'نصب سیستم آفلاین')
        self.log("📦 در حال نصب سیستم آفلاین...")

        try:
            # کپی تنظیمات آفلاین
            shutil.copy2('plasco/settings_offline.py', 'plasco/settings.py')
            self.log("✅ تنظیمات آفلاین کپی شد")
            return True
        except Exception as e:
            self.log(f"❌ خطا در نصب سیستم: {e}")
            return False

    def step3_create_database(self):
        """مرحله 3: ایجاد دیتابیس محلی"""
        self.update_progress(3, 'ایجاد دیتابیس محلی')
        self.log("🗄️ در حال ایجاد دیتابیس محلی...")

        commands = [
            'makemigrations',
            'migrate'
        ]

        for cmd in commands:
            if not self.run_management_command(cmd):
                return False

        self.log("✅ دیتابیس محلی ایجاد شد")
        return True

    def step4_clear_data(self):
        """مرحله 4: پاکسازی داده‌های موجود"""
        self.update_progress(4, 'پاکسازی داده‌های موجود')
        self.log("🧹 در حال پاکسازی داده‌های موجود...")

        # پاکسازی تمام داده‌ها از دیتابیس
        return self.run_management_command('clear_local_db --force')

    def step5_transfer_data(self):
        """مرحله 5: انتقال داده از سرور"""
        self.update_progress(5, 'انتقال داده از سرور')
        self.log("📥 در حال انتقال داده از سرور...")

        sync_commands = [
            'sync_full_cantact',
            'sync_full_account',
            'sync_full_dashbord',
            'sync_full_invoice',
            'sync_full_pos_payment'
        ]

        for cmd in sync_commands:
            if not self.run_management_command(cmd):
                self.log(f"⚠️ خطا در {cmd} - ادامه می‌دهیم")
                continue

        self.log("✅ انتقال داده کامل شد")
        return True

    def step6_create_superuser(self):
        """مرحله 6: ایجاد کاربر مدیر"""
        self.update_progress(6, 'ایجاد کاربر مدیر')
        self.log("👑 در حال ایجاد کاربر مدیر...")

        try:
            # حذف کاربر قبلی اگر وجود دارد
            self.run_management_command(
                f'shell -c "from django.contrib.auth.models import User; User.objects.filter(username=\'{self.client_ip}\').delete()"')

            # ایجاد کاربر جدید
            create_cmd = f'createsuperuser --username {self.client_ip} --email {self.client_ip}@local.plasco --noinput'
            if self.run_management_command(create_cmd):
                # تنظیم رمز عبور
                password_cmd = f'shell -c "\nfrom django.contrib.auth.models import User\nuser = User.objects.get(username=\'{self.client_ip}\')\nuser.set_password(\'{self.client_ip}\')\nuser.save()\nprint(\"کاربر ایجاد شد\")\n"'
                self.run_management_command(password_cmd)
                self.log(f"✅ کاربر مدیر ایجاد شد: {self.client_ip}/{self.client_ip}")
                return True
            else:
                return False

        except Exception as e:
            self.log(f"❌ خطا در ایجاد کاربر مدیر: {e}")
            return False

    def step7_clear_sync_logs(self):
        """مرحله 7: پاکسازی لاگ‌های سینک"""
        self.update_progress(7, 'پاکسازی لاگ‌های سینک')
        self.log("📝 در حال پاکسازی لاگ‌های سینک...")

        return self.run_management_command('clear_all_sync_logs --force')

    def run_installation(self):
        """اجرای کامل فرآیند نصب"""
        self.log("🚀 شروع فرآیند نصب آفلاین...")

        steps = [
            (1, "بررسی نصب قبلی", self.step1_check_installation),
            (2, "نصب سیستم آفلاین", self.step2_install_system),
            (3, "ایجاد دیتابیس محلی", self.step3_create_database),
            (4, "پاکسازی داده‌های موجود", self.step4_clear_data),
            (5, "انتقال داده از سرور", self.step5_transfer_data),
            (6, "ایجاد کاربر مدیر", self.step6_create_superuser),
            (7, "پاکسازی لاگ‌های سینک", self.step7_clear_sync_logs)
        ]

        for step_number, step_name, step_func in steps:
            self.log(f"🔧 شروع مرحله {step_number}: {step_name}")

            if not step_func():
                self.log(f"❌ نصب در مرحله {step_number} متوقف شد")
                self.update_progress(step_number, 'خطا - نصب متوقف شد', 'error')
                return False

            self.log(f"✅ مرحله {step_number} تکمیل شد")
            time.sleep(1)  # تأثیر بصری

        self.update_progress(7, 'نصب کامل شد', 'completed')
        self.log("🎉 نصب سیستم آفلاین با موفقیت انجام شد!")
        return True


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("استفاده: python offline_installer.py <CLIENT_IP> <SERVER_URL>")
        sys.exit(1)

    client_ip = sys.argv[1]
    server_url = sys.argv[2]

    installer = OfflineInstaller(client_ip, server_url)
    success = installer.run_installation()

    if success:
        print("\n" + "=" * 50)
        print("✅ نصب کامل شد!")
        print(f"👤 نام کاربری: {client_ip}")
        print(f"🔑 رمز عبور: {client_ip}")
        print("🌐 آدرس: http://localhost:8000")
        print("=" * 50)
    else:
        print("\n❌ نصب با خطا مواجه شد. لطفاً فایل install_log.txt را بررسی کنید.")

    sys.exit(0 if success else 1)