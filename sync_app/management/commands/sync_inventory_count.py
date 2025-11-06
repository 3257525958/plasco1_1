from django.core.management.base import BaseCommand
from django.conf import settings
import requests
from django.apps import apps
from plasco.sync_service import sync_service


class Command(BaseCommand):
    help = 'انتقال کامل InventoryCount با استفاده از endpoint اصلی سینک'

    def handle(self, *args, **options):
        if not settings.OFFLINE_MODE:
            self.stdout.write("❌ فقط در حالت آفلاین قابل اجراست")
            return

        self.stdout.write("🚀 شروع انتقال InventoryCount با endpoint اصلی...")

        try:
            # تست اتصال به سرور
            if not sync_service.check_internet_connection():
                self.stdout.write("❌ اتصال به سرور برقرار نیست")
                return

            # دریافت داده از endpoint اصلی سینک
            self.stdout.write("📥 دریافت داده از سرور...")
            response = requests.get(
                f"{settings.ONLINE_SERVER_URL}/api/sync/pull/",
                timeout=60
            )

            if response.status_code != 200:
                self.stdout.write(f"❌ خطا در دریافت داده: {response.status_code}")
                return

            data = response.json()

            if data.get('status') != 'success':
                self.stdout.write(f"❌ خطا از سمت سرور: {data.get('message')}")
                return

            all_changes = data.get('changes', [])
            self.stdout.write(f"📦 کل رکوردهای قابل دریافت: {len(all_changes)}")

            # فیلتر کردن فقط InventoryCount
            inventory_changes = []
            for change in all_changes:
                if (change.get('app_name') == 'account_app' and
                        change.get('model_type') == 'InventoryCount'):
                    inventory_changes.append(change)

            self.stdout.write(f"🎯 رکوردهای InventoryCount: {len(inventory_changes)}")

            if not inventory_changes:
                self.stdout.write("⚠️ هیچ داده‌ای برای InventoryCount یافت نشد")
                return

            # پردازش داده‌ها
            model_class = apps.get_model('account_app', 'InventoryCount')
            saved_count = self.process_inventory_changes(model_class, inventory_changes)

            self.stdout.write(
                self.style.SUCCESS(f"🎉 انتقال کامل شد! {saved_count} رکورد")
            )

            # بررسی نهایی
            final_count = model_class.objects.count()
            self.stdout.write(f"📊 تعداد نهایی در دیتابیس لوکال: {final_count}")

        except Exception as e:
            self.stdout.write(f"❌ خطا: {e}")

    def process_inventory_changes(self, model_class, changes):
        """پردازش تغییرات InventoryCount"""
        saved_count = 0

        for change in changes:
            try:
                record_id = change.get('record_id')
                action = change.get('action')
                data = change.get('data', {})

                if action == 'delete':
                    # حذف رکورد
                    model_class.objects.filter(id=record_id).delete()
                    self.stdout.write(f"🗑️ حذف شد: {record_id}")
                else:
                    # ایجاد یا آپدیت رکورد
                    processed_data = self.process_inventory_data(data)

                    obj, created = model_class.objects.update_or_create(
                        id=record_id,
                        defaults=processed_data
                    )

                    saved_count += 1
                    action_text = "ایجاد" if created else "آپدیت"

                    if saved_count % 100 == 0:
                        self.stdout.write(f"📝 {saved_count} رکورد پردازش شد...")

            except Exception as e:
                error_msg = str(e)
                if "FOREIGN KEY" not in error_msg:
                    self.stdout.write(f"⚠️ خطا در رکورد {record_id}: {e}")
                continue

        return saved_count

    def process_inventory_data(self, data):
        """پردازش داده‌های InventoryCount"""
        processed_data = {}

        # فیلدهای اصلی InventoryCount
        inventory_fields = [
            'product_name', 'is_new', 'quantity', 'count_date',
            'created_at', 'barcode_data', 'selling_price',
            'branch_id', 'counter_id', 'profit_percentage'
        ]

        for field in inventory_fields:
            if field in data:
                value = data[field]

                # مدیریت مقادیر خاص
                if value is None:
                    processed_data[field] = None
                elif field in ['selling_price', 'profit_percentage'] and isinstance(value, (int, float)):
                    from decimal import Decimal
                    processed_data[field] = Decimal(str(value))
                elif field.endswith('_id') and isinstance(value, int):
                    processed_data[field] = value
                else:
                    processed_data[field] = value

        return processed_data