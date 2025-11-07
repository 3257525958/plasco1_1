from django.core.management.base import BaseCommand
from django.conf import settings
from sync_app.sync_service import sync_service  # ✅ تغییر این خط


class Command(BaseCommand):
    help = 'شروع سرویس سینک خودکار'

    def handle(self, *args, **options):
        if not getattr(settings, 'OFFLINE_MODE', False):
            self.stdout.write(
                self.style.WARNING('❌ این دستور فقط در حالت آفلاین قابل اجراست')
            )
            return

        self.stdout.write('🚀 شروع سرویس سینک خودکار...')

        try:
            sync_service.start_auto_sync()
            self.stdout.write(
                self.style.SUCCESS('✅ سرویس سینک خودکار با موفقیت شروع شد')
            )
            self.stdout.write(f'⏰ بازه سینک: هر {getattr(settings, "SYNC_INTERVAL", 300)} ثانیه')

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ خطا در شروع سرویس: {e}')
            )