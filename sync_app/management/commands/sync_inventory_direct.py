from django.core.management.base import BaseCommand
from django.conf import settings
import requests
import sqlite3
import os
from django.db import connection


class Command(BaseCommand):
    help = 'انتقال مستقیم InventoryCount با SQLite خام'

    def handle(self, *args, **options):
        if not settings.OFFLINE_MODE:
            self.stdout.write("❌ فقط در حالت آفلاین قابل اجراست")
            return

        self.stdout.write("🚀 شروع انتقال مستقیم InventoryCount...")

        try:
            # 1. دریافت داده از سرور
            self.stdout.write("📡 دریافت داده از سرور...")
            response = requests.get(
                f"{settings.ONLINE_SERVER_URL}/api/sync/model-data/",
                params={'app': 'account_app', 'model': 'InventoryCount'},
                timeout=60
            )

            if response.status_code != 200:
                self.stdout.write(f"❌ خطای HTTP: {response.status_code}")
                return

            data = response.json()
            if data.get('status') != 'success':
                self.stdout.write(f"❌ وضعیت ناموفق: {data}")
                return

            records = data.get('records', [])
            self.stdout.write(f"📊 تعداد رکوردها: {len(records)}")

            if not records:
                self.stdout.write("⚠️ هیچ رکوردی برای انتقال وجود ندارد")
                return

            # 2. اتصال مستقیم به دیتابیس SQLite
            db_path = os.path.join(settings.BASE_DIR, 'db_offline.sqlite3')
            self.stdout.write(f"🔗 اتصال به دیتابیس: {db_path}")

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # 3. ایجاد جدول اگر وجود ندارد (برای اطمینان)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS account_app_inventorycount (
                    id INTEGER PRIMARY KEY,
                    product_name TEXT,
                    is_new BOOLEAN,
                    quantity INTEGER,
                    count_date TEXT,
                    created_at TEXT,
                    barcode_data TEXT,
                    selling_price INTEGER,
                    branch_id INTEGER,
                    counter_id INTEGER,
                    profit_percentage REAL
                )
            """)

            # 4. انتقال رکوردها
            saved_count = 0
            error_count = 0

            for record in records:
                try:
                    # تبدیل داده‌ها به فرمت مناسب
                    record_id = record.get('id')
                    product_name = record.get('product_name', '')
                    is_new = 1 if record.get('is_new') else 0
                    quantity = record.get('quantity', 0)
                    count_date = record.get('count_date', '1403/01/01')
                    created_at = record.get('created_at', '2024-01-01 00:00:00')
                    barcode_data = record.get('barcode_data', '')
                    selling_price = record.get('selling_price', 0)

                    # مدیریت branch_id
                    branch_id = record.get('branch_id', 1)
                    if branch_id not in [1, 2, 3]:  # فقط branchهای موجود
                        branch_id = 1

                    # مدیریت counter_id
                    counter_id = record.get('counter_id', 1)
                    if counter_id not in [1, 2, 3]:  # فقط userهای موجود
                        counter_id = 1

                    profit_percentage = float(record.get('profit_percentage', 0.0))

                    # درج یا جایگزینی رکورد
                    cursor.execute("""
                        INSERT OR REPLACE INTO account_app_inventorycount 
                        (id, product_name, is_new, quantity, count_date, created_at, 
                         barcode_data, selling_price, branch_id, counter_id, profit_percentage)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        record_id, product_name, is_new, quantity, count_date, created_at,
                        barcode_data, selling_price, branch_id, counter_id, profit_percentage
                    ))

                    saved_count += 1

                    if saved_count % 500 == 0:
                        self.stdout.write(f"📝 {saved_count} رکورد انتقال یافت...")

                except Exception as e:
                    error_count += 1
                    if error_count <= 5:
                        self.stdout.write(f"❌ خطا در رکورد {record.get('id')}: {e}")
                    continue

            # کامیت تغییرات
            conn.commit()
            conn.close()

            self.stdout.write(f"🎯 انتقال کامل: {saved_count} رکورد ذخیره شد")
            if error_count > 0:
                self.stdout.write(f"⚠️ خطاها: {error_count} رکورد")

            # 5. تأیید نهایی
            self.verify_transfer()

        except Exception as e:
            self.stdout.write(f"❌ خطای کلی: {e}")

    def verify_transfer(self):
        """تأیید انتقال"""
        try:
            from account_app.models import InventoryCount
            count = InventoryCount.objects.count()
            self.stdout.write(f"✅ تأیید نهایی: {count} رکورد InventoryCount در دیتابیس")

            # نمایش نمونه‌ای از داده‌ها
            if count > 0:
                sample = InventoryCount.objects.first()
                self.stdout.write(f"📝 نمونه: {sample.product_name} - {sample.quantity}")

        except Exception as e:
            self.stdout.write(f"⚠️ خطا در تأیید: {e}")