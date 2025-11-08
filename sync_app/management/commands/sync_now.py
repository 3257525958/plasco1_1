from django.core.management.base import BaseCommand
from django.conf import settings
from sync_app.sync_service import sync_service  # ✅ تغییر این خط
# management/commands/sync_now.py
from django.core.management.base import BaseCommand
from sync_app.sync_service import sync_service


class Command(BaseCommand):
    help = 'انجام سینک فوری با قابلیت تشخیص تغییرات واقعی'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='اجبار به سینک کامل بدون درنظرگیری timestamp',
        )

    def handle(self, *args, **options):
        if options['force']:
            self.stdout.write("🔄 سینک اجباری در حال اجرا...")
            result = sync_service.full_sync()
        else:
            self.stdout.write("🔍 سینک هوشمند در حال اجرا...")
            result = sync_service.bidirectional_sync()

        # نمایش نتایج دقیق
        self.stdout.write(
            self.style.SUCCESS(
                f"✅ سینک کامل شد\n"
                f"📤 ارسال شده به سرور: {result.get('sent_to_server', 0)}\n"
                f"📥 دریافت شده از سرور: {result.get('received_from_server', 0)}\n"
                f"📊 مجموع واقعی: {result.get('total', 0)}"
            )
        )
