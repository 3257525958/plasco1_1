from django.core.management.base import BaseCommand
from sync_service import sync_service


class Command(BaseCommand):
    help = 'توقف سرویس سینک خودکار'

    def handle(self, *args, **options):
        self.stdout.write('🛑 توقف سرویس سینک خودکار...')

        try:
            sync_service.stop_auto_sync()
            self.stdout.write(
                self.style.SUCCESS('✅ سرویس سینک خودکار با موفقیت متوقف شد')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ خطا در توقف سرویس: {e}')
            )