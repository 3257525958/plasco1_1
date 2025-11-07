from django.core.management.base import BaseCommand
from django.conf import settings
from sync_app.sync_service import sync_service  # ✅ تغییر این خط

class Command(BaseCommand):
    help = 'اجرای فوری سینک دوطرفه'

    def handle(self, *args, **options):
        if not getattr(settings, 'OFFLINE_MODE', False):
            self.stdout.write(
                self.style.WARNING('❌ این دستور فقط در حالت آفلاین قابل اجراست')
            )
            return

        self.stdout.write('⚡ اجرای فوری سینک دوطرفه...')

        try:
            result = sync_service.bidirectional_sync()

            self.stdout.write(
                self.style.SUCCESS('✅ سینک فوری با موفقیت انجام شد')
            )
            self.stdout.write(f'📤 ارسال شده به سرور: {result.get("sent_to_server", 0)}')
            self.stdout.write(f'📥 دریافت شده از سرور: {result.get("received_from_server", 0)}')
            self.stdout.write(f'📊 مجموع: {result.get("total", 0)}')

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ خطا در سینک فوری: {e}')
            )