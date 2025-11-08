from django.core.management.base import BaseCommand
import os
from django.conf import settings
from django.db import connection


class Command(BaseCommand):
    help = 'پاک کردن کامل دیتابیس لوکال (SQLite)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='اجرای فوری بدون تأیید',
        )

    def handle(self, *args, **options):
        # فقط در حالت آفلاین اجرا شود
        if not getattr(settings, 'OFFLINE_MODE', False):
            self.stdout.write(
                self.style.ERROR('❌ این دستور فقط در حالت آفلاین قابل اجراست')
            )
            return

        self.stdout.write(self.style.WARNING('🚨 ⚠️  ⚠️  ⚠️  هشدار جدی  ⚠️  ⚠️  ⚠️'))
        self.stdout.write('=' * 50)
        self.stdout.write('این دستور تمام داده‌های دیتابیس لوکال را پاک می‌کند!')
        self.stdout.write('تمامی اطلاعات شامل:')
        self.stdout.write('  - کاربران')
        self.stdout.write('  - محصولات')
        self.stdout.write('  - فاکتورها')
        self.stdout.write('  - تراکنش‌ها')
        self.stdout.write('  - و تمام داده‌های دیگر')
        self.stdout.write('=' * 50)
        self.stdout.write(self.style.ERROR('❌ این عمل غیرقابل بازگشت است!'))

        # درخواست تأیید
        if not options['force']:
            confirm = input(
                self.style.WARNING('🔥 آیا مطمئن هستید که می‌خواهید ادامه دهید؟ (yes/No): ')
            )
            if confirm.lower() not in ['yes', 'y', 'بله']:
                self.stdout.write('❌ عملیات لغو شد')
                return

        try:
            # بستن اتصال دیتابیس
            connection.close()

            # پیدا کردن مسیر فایل دیتابیس
            db_path = settings.DATABASES['default']['NAME']

            self.stdout.write(f'🔍 مسیر دیتابیس: {db_path}')

            if os.path.exists(db_path):
                # پاک کردن فایل دیتابیس
                os.remove(db_path)
                self.stdout.write(self.style.SUCCESS('✅ فایل دیتابیس لوکال پاک شد'))

                # اجرای migrations برای ایجاد دیتابیس خالی
                self.stdout.write('🔧 در حال ایجاد دیتابیس خالی...')
                os.system('python manage.py makemigrations')
                os.system('python manage.py migrate')

                self.stdout.write(self.style.SUCCESS('✅ دیتابیس خالی ایجاد شد'))

                # ایجاد کاربر ادمین پیش‌فرض
                self.stdout.write('👤 در حال ایجاد کاربر ادمین...')
                from django.contrib.auth.models import User
                if not User.objects.filter(username='admin').exists():
                    User.objects.create_superuser('admin', 'admin@example.com', 'admin')
                    self.stdout.write(self.style.SUCCESS('✅ کاربر ادمین ایجاد شد'))
                else:
                    self.stdout.write('✅ کاربر ادمین موجود است')

            else:
                self.stdout.write('⚠️ فایل دیتابیس پیدا نشد')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ خطا در پاک کردن دیتابیس: {e}'))

        self.stdout.write(self.style.SUCCESS('🎉 عملیات پاک کردن دیتابیس لوکال کامل شد'))