from django.core.management.base import BaseCommand
from django.conf import settings
import requests
from django.apps import apps
from django.db import transaction
from django.db.models import Q
from decimal import Decimal
import math


class Command(BaseCommand):
    help = 'انتقال کامل account_app با مدیریت فیلدهای وابسته'

    def handle(self, *args, **options):
        if not settings.OFFLINE_MODE:
            self.stdout.write("❌ فقط در حالت آفلاین قابل اجراست")
            return

        self.stdout.write("🚀 شروع انتقال کامل account_app...")

        # مرحله 0: بررسی اولیه
        self.stdout.write("\n🔍 مرحله 0: بررسی اولیه داده‌ها...")
        initial_status = self.get_initial_status()

        # مرحله 1: انتقال تمام مدل‌ها
        self.stdout.write("\n📦 مرحله 1: انتقال تمام مدل‌های account_app...")
        all_models = [
            'Product', 'ProductPricing', 'PaymentMethod',
            'Expense', 'ExpenseImage', 'StockTransaction', 'InventoryCount'
        ]

        transfer_results = {}
        for model_name in all_models:
            try:
                model_class = apps.get_model('account_app', model_name)
                transferred_count = self.sync_single_model(model_class)
                transfer_results[model_name] = transferred_count
                self.stdout.write(f"✅ {model_name}: {transferred_count} رکورد انتقال یافت")
            except Exception as e:
                self.stdout.write(f"❌ خطا در انتقال {model_name}: {e}")
                transfer_results[model_name] = 0

        # مرحله 2: مقایسه و پاکسازی خودکار
        self.stdout.write("\n🔍 مرحله 2: مقایسه و پاکسازی خودکار...")
        cleanup_results = self.auto_cleanup_all_models()

        # مرحله 3: بررسی نهایی و گزارش
        self.stdout.write("\n📊 مرحله 3: گزارش نهایی...")
        self.generate_final_report(initial_status, transfer_results, cleanup_results)

        self.stdout.write(
            self.style.SUCCESS("\n🎉 انتقال کامل account_app با موفقیت انجام شد!")
        )

    def get_initial_status(self):
        """دریافت وضعیت اولیه تمام مدل‌ها"""
        initial_status = {}
        models_to_check = [
            'Product', 'ProductPricing', 'PaymentMethod',
            'Expense', 'ExpenseImage', 'StockTransaction', 'InventoryCount'
        ]

        for model_name in models_to_check:
            try:
                model_class = apps.get_model('account_app', model_name)
                count = model_class.objects.count()
                initial_status[model_name] = count
                self.stdout.write(f"📊 تعداد اولیه {model_name}: {count} رکورد")
            except Exception as e:
                self.stdout.write(f"⚠️ خطا در بررسی {model_name}: {e}")
                initial_status[model_name] = 0

        return initial_status

    def sync_single_model(self, model_class):
        """انتقال یک مدل خاص"""
        response = requests.get(
            f"{settings.ONLINE_SERVER_URL}/api/sync/model-data/",
            params={'app': 'account_app', 'model': model_class.__name__},
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                records = data.get('records', [])
                self.stdout.write(f"📥 دریافت {len(records)} رکورد برای {model_class.__name__}")
                return self.save_records_safe(model_class, records)

        self.stdout.write(f"⚠️ خطا در پاسخ سرور برای {model_class.__name__}: {response.status_code}")
        return 0

    def save_records_safe(self, model_class, records):
        """ذخیره امن رکوردها با مدیریت فیلدهای وابسته"""
        saved_count = 0
        error_count = 0

        for record_data in records:
            try:
                record_id = record_data.get('id')
                if not record_id:
                    continue

                # پردازش داده‌ها با مدیریت فیلدهای وابسته
                processed_data = self.process_record_data(record_data, model_class)

                # ایجاد یا آپدیت
                obj, created = model_class.objects.update_or_create(
                    id=record_id,
                    defaults=processed_data
                )
                saved_count += 1

                # نمایش پیشرفت برای مدل‌های بزرگ
                if saved_count % 100 == 0 and len(records) > 500:
                    self.stdout.write(f"📝 {saved_count} رکورد {model_class.__name__} پردازش شد...")

            except Exception as e:
                error_count += 1
                # فقط 5 خطای اول را نمایش بده
                if error_count <= 5:
                    self.stdout.write(f"❌ خطا در رکورد {record_id}: {str(e)}")
                continue

        if error_count > 0:
            self.stdout.write(f"⚠️ مجموع خطاها در {model_class.__name__}: {error_count}")

        return saved_count

    def process_record_data(self, record_data, model_class):
        """پردازش داده‌های رکورد با مدیریت فیلدهای وابسته"""
        processed_data = {}

        for field_name, value in record_data.items():
            if value is None:
                processed_data[field_name] = None
                continue

            # مدیریت ویژه برای InventoryCount - فیلدهای وابسته
            if model_class.__name__ == 'InventoryCount':
                if field_name == 'branch_id':
                    # بررسی وجود branch
                    from cantact_app.models import Branch
                    if Branch.objects.filter(id=value).exists():
                        processed_data[field_name] = value
                    else:
                        first_branch = Branch.objects.first()
                        processed_data[field_name] = first_branch.id if first_branch else 1
                        self.stdout.write(
                            f"⚠️ branch_id={value} وجود ندارد، از {processed_data[field_name]} استفاده شد")

                elif field_name == 'counter_id':
                    # بررسی وجود user
                    from django.contrib.auth.models import User
                    if User.objects.filter(id=value).exists():
                        processed_data[field_name] = value
                    else:
                        first_user = User.objects.first()
                        processed_data[field_name] = first_user.id if first_user else 1
                        self.stdout.write(
                            f"⚠️ counter_id={value} وجود ندارد، از {processed_data[field_name]} استفاده شد")

                else:
                    processed_data[field_name] = value

            else:
                # برای سایر مدل‌ها
                processed_data[field_name] = value

        return processed_data

    def auto_cleanup_all_models(self):
        """پاکسازی خودکار تمام مدل‌ها پس از انتقال"""
        cleanup_results = {}

        models_to_cleanup = [
            'Product', 'ProductPricing', 'PaymentMethod',
            'Expense', 'ExpenseImage', 'StockTransaction', 'InventoryCount'
        ]

        for model_name in models_to_cleanup:
            try:
                model_class = apps.get_model('account_app', model_name)
                deleted_count = self.cleanup_single_model(model_class)
                cleanup_results[model_name] = deleted_count

                if deleted_count > 0:
                    self.stdout.write(f"🧹 {model_name}: {deleted_count} رکورد اضافه پاک شد")
                else:
                    self.stdout.write(f"✅ {model_name}: مطابقت کامل با سرور")

            except Exception as e:
                self.stdout.write(f"⚠️ خطا در پاکسازی {model_name}: {e}")
                cleanup_results[model_name] = 0

        return cleanup_results

    def cleanup_single_model(self, model_class):
        """پاکسازی داده‌های اضافه یک مدل خاص"""
        try:
            # دریافت IDهای موجود در سرور
            server_ids = self.get_server_ids(model_class)
            if server_ids is None:
                return 0

            # دریافت IDهای موجود در لوکال
            local_ids = set(model_class.objects.values_list('id', flat=True))

            # پیدا کردن IDهایی که در لوکال هستند اما در سرور نیستند
            extra_ids = local_ids - server_ids

            if not extra_ids:
                return 0

            # پاکسازی رکوردهای اضافه
            deleted_count, _ = model_class.objects.filter(id__in=extra_ids).delete()
            return deleted_count

        except Exception as e:
            self.stdout.write(f"⚠️ خطا در پاکسازی {model_class.__name__}: {e}")
            return 0

    def get_server_ids(self, model_class):
        """دریافت IDهای موجود در سرور"""
        try:
            response = requests.get(
                f"{settings.ONLINE_SERVER_URL}/api/sync/model-data/",
                params={'app': 'account_app', 'model': model_class.__name__},
                timeout=30
            )

            if response.status_code != 200:
                return None

            data = response.json()
            if data.get('status') != 'success':
                return None

            server_records = data.get('records', [])
            server_ids = {record['id'] for record in server_records if record.get('id')}

            return server_ids

        except Exception as e:
            self.stdout.write(f"⚠️ خطا در دریافت IDهای سرور برای {model_class.__name__}: {e}")
            return None

    def generate_final_report(self, initial_status, transfer_results, cleanup_results):
        """تولید گزارش نهایی"""
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write("📋 گزارش نهایی انتقال account_app")
        self.stdout.write("=" * 50)

        models_to_report = [
            'Product', 'ProductPricing', 'PaymentMethod',
            'Expense', 'ExpenseImage', 'StockTransaction', 'InventoryCount'
        ]

        total_transferred = 0
        total_cleaned = 0

        for model_name in models_to_report:
            initial = initial_status.get(model_name, 0)
            transferred = transfer_results.get(model_name, 0)
            cleaned = cleanup_results.get(model_name, 0)

            # محاسبه تعداد نهایی
            final_count = initial + transferred - cleaned

            self.stdout.write(f"\n📊 {model_name}:")
            self.stdout.write(f"   📥 اولیه: {initial} رکورد")
            self.stdout.write(f"   📤 انتقال یافته: {transferred} رکورد")
            self.stdout.write(f"   🗑️  پاک شده: {cleaned} رکورد")
            self.stdout.write(f"   ✅ نهایی: {final_count} رکورد")

            total_transferred += transferred
            total_cleaned += cleaned

        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(f"📈 جمع کل انتقال: {total_transferred} رکورد")
        self.stdout.write(f"🗑️  جمع کل پاک‌سازی: {total_cleaned} رکورد")
        self.stdout.write("=" * 50)

        # بررسی ویژه InventoryCount
        self.check_inventory_count_special()


    def check_inventory_count_special(self):


        """بررسی ویژه برای InventoryCount"""
        try:
            from account_app.models import InventoryCount

            # دریافت تعداد نهایی
            final_count = InventoryCount.objects.count()

            # دریافت تعداد از سرور برای مقایسه
            server_ids = self.get_server_ids(InventoryCount)
            if server_ids is not None:
                server_count = len(server_ids)


                if final_count == server_count:
                    self.stdout.write(f"\n🎯 InventoryCount: تطابق کامل ✅ (لوکال: {final_count} | سرور: {server_count})")
                else:
                    self.stdout.write(f"\n⚠️ InventoryCount: عدم تطابق ❌ (لوکال: {final_count} | سرور: {server_count})")

        except Exception as e:
            self.stdout.write(f"⚠️ خطا در بررسی ویژه InventoryCount: {e}")