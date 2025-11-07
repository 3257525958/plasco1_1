from django.core.management.base import BaseCommand
from sync_app.models import DataSyncLog
from django.utils import timezone


class Command(BaseCommand):
    help = 'پاکسازی کامل تمام داده‌های DataSyncLog'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='اجرای فوری بدون تأیید',
        )
        parser.add_argument(
            '--yes',
            action='store_true',
            help='تأیید خودکار همه سوالات',
        )

    def handle(self, *args, **options):
        force = options['force']
        yes = options['yes']

        # شمارش تعداد رکوردها
        total_count = DataSyncLog.objects.count()
        synced_count = DataSyncLog.objects.filter(sync_status=True).count()
        unsynced_count = DataSyncLog.objects.filter(sync_status=False).count()

        if total_count == 0:
            self.stdout.write(
                self.style.SUCCESS('✅ هیچ داده‌ای در DataSyncLog وجود ندارد')
            )
            return

        self.stdout.write('🚨 ⚠️  ⚠️  ⚠️  هشدار جدی  ⚠️  ⚠️  ⚠️')
        self.stdout.write('=' * 50)
        self.stdout.write(f'📊 آمار فعلی DataSyncLog:')
        self.stdout.write(f'   📋 مجموع رکوردها: {total_count}')
        self.stdout.write(f'   ✅ سینک شده: {synced_count}')
        self.stdout.write(f'   ⏳ در انتظار سینک: {unsynced_count}')
        self.stdout.write('=' * 50)
        self.stdout.write(
            self.style.ERROR('❌ این عمل تمام داده‌های سینک را پاک می‌کند!')
        )
        self.stdout.write(
            self.style.WARNING('⚠️  تغییرات سینک نشده برای همیشه از دست خواهند رفت!')
        )

        # درخواست تأیید
        if not force and not yes:
            confirm = input(
                self.style.WARNING('🔥 آیا مطمئن هستید که می‌خواهید ادامه دهید؟ (y/N): ')
            )
            if confirm.lower() not in ['y', 'yes', 'بله']:
                self.stdout.write('❌ عملیات لغو شد')
                return

        # اجرای پاکسازی
        self.stdout.write('🧹 در حال پاکسازی تمام داده‌های DataSyncLog...')

        try:
            # پاکسازی تمام رکوردها
            deleted_count = DataSyncLog.objects.all().delete()[0]

            self.stdout.write(
                self.style.SUCCESS(f'✅ پاکسازی کامل انجام شد!')
            )
            self.stdout.write(f'🗑️  تعداد رکوردهای پاک شده: {deleted_count}')
            self.stdout.write(f'🕒 زمان: {timezone.now()}')

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ خطا در پاکسازی: {e}')
            )
