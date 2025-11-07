from django.core.management.base import BaseCommand
from sync_app.models import DataSyncLog
from django.utils import timezone
from datetime import timedelta

class Command(BaseCommand):
    help = 'پاکسازی لاگ‌های سینک قدیمی'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='حذف لاگ‌های قدیمی‌تر از این تعداد روز (پیش‌فرض: 30 روز)'
        )

    def handle(self, *args, **options):
        days = options['days']
        cutoff_date = timezone.now() - timedelta(days=days)

        self.stdout.write(f'🧹 پاکسازی لاگ‌های سینک قدیمی‌تر از {days} روز...')

        # فقط لاگ‌های سینک شده را پاکسازی می‌کنیم
        old_logs = DataSyncLog.objects.filter(
            sync_status=True,
            created_at__lt=cutoff_date
        )

        count = old_logs.count()
        old_logs.delete()

        self.stdout.write(
            self.style.SUCCESS(f'✅ {count} لاگ قدیمی پاکسازی شد')
        )