from django.core.management.base import BaseCommand
from django.conf import settings
import requests
from django.apps import apps
from django.utils import timezone


class Command(BaseCommand):
    help = 'انتقال کامل تمام داده‌های cantact_app از سرور به لوکال'

    def handle(self, *args, **options):
        if not settings.OFFLINE_MODE:
            self.stdout.write("❌ فقط در حالت آفلاین قابل اجراست")
            return

        self.stdout.write("🚀 شروع انتقال کامل cantact_app از سرور به لوکال...")

        # مدل‌های cantact_app
        models_to_sync = [
            'Branch', 'BranchAdmin', 'accuntmodel',
            'dataacont', 'phonnambermodel', 'savecodphon'
        ]

        total_synced = 0

        for model_name in models_to_sync:
            try:
                model_class = apps.get_model('cantact_app', model_name)
                synced_count = self.sync_model_data(model_class)
                total_synced += synced_count
                self.stdout.write(f"✅ {model_name}: {synced_count} رکورد")
            except Exception as e:
                self.stdout.write(f"❌ خطا در {model_name}: {e}")

        self.stdout.write(
            self.style.SUCCESS(f"🎉 انتقال کامل شد! مجموع: {total_synced} رکورد")
        )

    def sync_model_data(self, model_class):
        """دریافت و ذخیره داده‌های یک مدل از سرور"""
        try:
            # درخواست مستقیم از سرور برای داده‌های این مدل
            response = requests.get(
                f"{settings.ONLINE_SERVER_URL}/api/sync/model-data/",
                params={'app': 'cantact_app', 'model': model_class.__name__},
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    records = data.get('records', [])
                    return self.save_records(model_class, records)

            return 0

        except Exception as e:
            self.stdout.write(f"⚠️ خطا در دریافت داده‌های {model_class.__name__}: {e}")
            return 0

    def save_records(self, model_class, records):
        """ذخیره رکوردها در دیتابیس لوکال"""
        saved_count = 0

        for record_data in records:
            try:
                # استخراج ID از داده‌ها
                record_id = record_data.get('id')
                if not record_id:
                    continue

                # ایجاد یا آپدیت رکورد
                obj, created = model_class.objects.update_or_create(
                    id=record_id,
                    defaults=record_data
                )
                saved_count += 1

            except Exception as e:
                self.stdout.write(f"⚠️ خطا در ذخیره رکورد {record_id}: {e}")
                continue

        return saved_count