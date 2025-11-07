from django.core.management.base import BaseCommand
from django.conf import settings
from sync_app.sync_service import sync_service  # ✅ اصلاح این خط
from sync_app.models import DataSyncLog
from django.utils import timezone


class Command(BaseCommand):
    help = 'نمایش وضعیت سینک'

    def handle(self, *args, **options):
        self.stdout.write('📊 وضعیت سیستم سینک')
        self.stdout.write('=' * 50)

        # وضعیت کلی
        self.stdout.write(f'🔧 حالت: {"🟢 آفلاین" if getattr(settings, "OFFLINE_MODE", False) else "🔵 آنلاین"}')
        self.stdout.write(f'🔄 سرویس: {"🟢 در حال اجرا" if sync_service.is_running else "🔴 متوقف"}')
        self.stdout.write(f'⏰ بازه سینک: هر {getattr(settings, "SYNC_INTERVAL", 300)} ثانیه')
        self.stdout.write(f'🌐 آدرس سرور: {getattr(settings, "ONLINE_SERVER_URL", "تعریف نشده")}')

        # آمار DataSyncLog
        total_logs = DataSyncLog.objects.count()
        unsynced_logs = DataSyncLog.objects.filter(sync_status=False).count()
        synced_logs = DataSyncLog.objects.filter(sync_status=True).count()

        self.stdout.write('\n📝 لاگ‌های سینک:')
        self.stdout.write(f'   📋 مجموع لاگ‌ها: {total_logs}')
        self.stdout.write(f'   ✅ سینک شده: {synced_logs}')
        self.stdout.write(f'   ⏳ در انتظار سینک: {unsynced_logs}')

        if unsynced_logs > 0:
            self.stdout.write(
                self.style.WARNING(f'⚠️ {unsynced_logs} تغییر در انتظار ارسال به سرور')
            )

        # آخرین سینک موفق
        last_sync = DataSyncLog.objects.filter(sync_status=True).order_by('-synced_at').first()
        if last_sync:
            self.stdout.write(f'🕒 آخرین سینک موفق: {last_sync.synced_at}')
        else:
            self.stdout.write(self.style.WARNING('🕒 هیچ سینک موفقی ثبت نشده است'))

        # وضعیت اتصال
        try:
            if sync_service.check_internet_connection():
                self.stdout.write(self.style.SUCCESS('🌐 اتصال به سرور: برقرار'))
            else:
                self.stdout.write(self.style.ERROR('🌐 اتصال به سرور: قطع'))
        except:
            self.stdout.write(self.style.ERROR('🌐 اتصال به سرور: نامشخص'))