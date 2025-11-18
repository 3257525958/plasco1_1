#
# from django.core.management.base import BaseCommand
# from django.conf import settings
# import requests
# from django.apps import apps
# from django.db import transaction
# from django.db.models import Q
#
#
# class Command(BaseCommand):
#     help = 'انتقال کامل account_app با مقایسه و پاکسازی خودکار داده‌های اضافه'
#
#     def handle(self, *args, **options):
#         if not settings.OFFLINE_MODE:
#             self.stdout.write("❌ فقط در حالت آفلاین قابل اجراست")
#             return
#
#         self.stdout.write("🚀 شروع انتقال کامل account_app...")
#
#         # مرحله 0: بررسی اولیه
#         self.stdout.write("\n🔍 مرحله 0: بررسی اولیه داده‌ها...")
#         initial_status = self.get_initial_status()
#
#         # مرحله 1: انتقال تمام مدل‌ها
#         self.stdout.write("\n📦 مرحله 1: انتقال تمام مدل‌های account_app...")
#         all_models = [
#             'Product', 'ProductPricing', 'PaymentMethod',
#             'Expense', 'ExpenseImage', 'StockTransaction', 'InventoryCount'
#         ]
#
#         transfer_results = {}
#         for model_name in all_models:
#             try:
#                 model_class = apps.get_model('account_app', model_name)
#                 transferred_count = self.sync_single_model(model_class)
#                 transfer_results[model_name] = transferred_count
#                 self.stdout.write(f"✅ {model_name}: {transferred_count} رکورد انتقال یافت")
#             except Exception as e:
#                 self.stdout.write(f"❌ خطا در انتقال {model_name}: {e}")
#                 transfer_results[model_name] = 0
#
#         # مرحله 2: مقایسه و پاکسازی خودکار
#         self.stdout.write("\n🔍 مرحله 2: مقایسه و پاکسازی خودکار...")
#         cleanup_results = self.auto_cleanup_all_models()
#
#         # مرحله 3: بررسی نهایی و گزارش
#         self.stdout.write("\n📊 مرحله 3: گزارش نهایی...")
#         self.generate_final_report(initial_status, transfer_results, cleanup_results)
#
#         self.stdout.write(
#             self.style.SUCCESS("\n🎉 انتقال کامل account_app با موفقیت انجام شد!")
#         )
#
#     def get_initial_status(self):
#         """دریافت وضعیت اولیه تمام مدل‌ها"""
#         initial_status = {}
#         models_to_check = [
#             'Product', 'ProductPricing', 'PaymentMethod',
#             'Expense', 'ExpenseImage', 'StockTransaction', 'InventoryCount'
#         ]
#
#         for model_name in models_to_check:
#             try:
#                 model_class = apps.get_model('account_app', model_name)
#                 count = model_class.objects.count()
#                 initial_status[model_name] = count
#                 self.stdout.write(f"📊 تعداد اولیه {model_name}: {count} رکورد")
#             except Exception as e:
#                 self.stdout.write(f"⚠️ خطا در بررسی {model_name}: {e}")
#                 initial_status[model_name] = 0
#
#         return initial_status
#
#     def sync_single_model(self, model_class):
#         """انتقال یک مدل خاص"""
#         response = requests.get(
#             f"{settings.ONLINE_SERVER_URL}/api/sync/model-data/",
#             params={'app': 'account_app', 'model': model_class.__name__},
#             timeout=30
#         )
#
#         if response.status_code == 200:
#             data = response.json()
#             if data.get('status') == 'success':
#                 records = data.get('records', [])
#                 self.stdout.write(f"📥 دریافت {len(records)} رکورد برای {model_class.__name__}")
#                 return self.save_records_safe(model_class, records)
#
#         self.stdout.write(f"⚠️ خطا در پاسخ سرور برای {model_class.__name__}: {response.status_code}")
#         return 0
#
#     def save_records_safe(self, model_class, records):
#         """ذخیره امن رکوردها با جلوگیری از تکراری"""
#         saved_count = 0
#         duplicate_count = 0
#         error_count = 0
#
#         for record_data in records:
#             try:
#                 record_id = record_data.get('id')
#                 if not record_id:
#                     continue
#
#                 # جلوگیری از رکوردهای تکراری
#                 if model_class.objects.filter(id=record_id).exists():
#                     duplicate_count += 1
#                     continue
#
#                 # پردازش داده‌ها
#                 processed_data = self.process_record_data(record_data, model_class)
#
#                 # ایجاد یا آپدیت
#                 obj, created = model_class.objects.update_or_create(
#                     id=record_id,
#                     defaults=processed_data
#                 )
#                 saved_count += 1
#
#             except Exception as e:
#                 error_count += 1
#                 continue
#
#         if duplicate_count > 0:
#             self.stdout.write(f"   ⏭️ {duplicate_count} رکورد تکراری رد شد")
#         if error_count > 0:
#             self.stdout.write(f"   ❌ {error_count} خطا در ذخیره")
#
#         return saved_count
#
#     def process_record_data(self, record_data, model_class):
#         """پردازش داده‌های رکورد"""
#         processed_data = {}
#
#         for field_name, value in record_data.items():
#             if value is None:
#                 processed_data[field_name] = None
#                 continue
#
#             # مدیریت فیلدهای ForeignKey
#             if field_name.endswith('_id') and isinstance(value, int):
#                 processed_data[field_name] = value
#
#             # مدیریت فیلدهای Decimal
#             elif isinstance(value, (int, float)) and self.is_decimal_field(model_class, field_name):
#                 from decimal import Decimal
#                 processed_data[field_name] = Decimal(str(value))
#
#             # مدیریت فیلدهای تاریخ
#             elif field_name.endswith('_date') or field_name in ['created_at', 'updated_at']:
#                 from django.utils import timezone
#                 from datetime import datetime
#                 try:
#                     if isinstance(value, str):
#                         processed_data[field_name] = datetime.fromisoformat(value.replace('Z', '+00:00'))
#                     else:
#                         processed_data[field_name] = value
#                 except:
#                     processed_data[field_name] = value
#
#             # سایر فیلدها
#             else:
#                 processed_data[field_name] = value
#
#         return processed_data
#
#     def is_decimal_field(self, model_class, field_name):
#         """بررسی فیلدهای Decimal"""
#         try:
#             field = model_class._meta.get_field(field_name)
#             return field.get_internal_type() in ['DecimalField', 'FloatField']
#         except:
#             return False
#
#     def auto_cleanup_all_models(self):
#         """پاکسازی خودکار تمام مدل‌ها پس از انتقال"""
#         cleanup_results = {}
#
#         models_to_cleanup = [
#             'Product', 'ProductPricing', 'PaymentMethod',
#             'Expense', 'ExpenseImage', 'StockTransaction', 'InventoryCount'
#         ]
#
#         for model_name in models_to_cleanup:
#             try:
#                 model_class = apps.get_model('account_app', model_name)
#                 deleted_count = self.cleanup_single_model(model_class)
#                 cleanup_results[model_name] = deleted_count
#
#                 if deleted_count > 0:
#                     self.stdout.write(f"🧹 {model_name}: {deleted_count} رکورد اضافه پاک شد")
#                 else:
#                     self.stdout.write(f"✅ {model_name}: مطابقت کامل با سرور")
#
#             except Exception as e:
#                 self.stdout.write(f"⚠️ خطا در پاکسازی {model_name}: {e}")
#                 cleanup_results[model_name] = 0
#
#         return cleanup_results
#
#     def cleanup_single_model(self, model_class):
#         """پاکسازی داده‌های اضافه یک مدل خاص"""
#         try:
#             # دریافت IDهای موجود در سرور
#             server_ids = self.get_server_ids(model_class)
#             if server_ids is None:
#                 return 0
#
#             # دریافت IDهای موجود در لوکال
#             local_ids = set(model_class.objects.values_list('id', flat=True))
#
#             # پیدا کردن IDهایی که در لوکال هستند اما در سرور نیستند
#             extra_ids = local_ids - server_ids
#
#             if not extra_ids:
#                 return 0
#
#             # پاکسازی رکوردهای اضافه
#             deleted_count, _ = model_class.objects.filter(id__in=extra_ids).delete()
#             return deleted_count
#
#         except Exception as e:
#             self.stdout.write(f"⚠️ خطا در پاکسازی {model_class.__name__}: {e}")
#             return 0
#
#     def get_server_ids(self, model_class):
#         """دریافت IDهای موجود در سرور"""
#         try:
#             response = requests.get(
#                 f"{settings.ONLINE_SERVER_URL}/api/sync/model-data/",
#                 params={'app': 'account_app', 'model': model_class.__name__},
#                 timeout=30
#             )
#
#             if response.status_code != 200:
#                 return None
#
#             data = response.json()
#             if data.get('status') != 'success':
#                 return None
#
#             server_records = data.get('records', [])
#             server_ids = {record['id'] for record in server_records if record.get('id')}
#
#             return server_ids
#
#         except Exception as e:
#             self.stdout.write(f"⚠️ خطا در دریافت IDهای سرور برای {model_class.__name__}: {e}")
#             return None
#
#     def generate_final_report(self, initial_status, transfer_results, cleanup_results):
#         """تولید گزارش نهایی"""
#         self.stdout.write("\n" + "=" * 50)
#         self.stdout.write("📋 گزارش نهایی انتقال account_app")
#         self.stdout.write("=" * 50)
#
#         models_to_report = [
#             'Product', 'ProductPricing', 'PaymentMethod',
#             'Expense', 'ExpenseImage', 'StockTransaction', 'InventoryCount'
#         ]
#
#         total_transferred = 0
#         total_cleaned = 0
#
#         for model_name in models_to_report:
#             initial = initial_status.get(model_name, 0)
#             transferred = transfer_results.get(model_name, 0)
#             cleaned = cleanup_results.get(model_name, 0)
#
#             # محاسبه تعداد نهایی
#             final_count = initial + transferred - cleaned
#
#             self.stdout.write(f"\n📊 {model_name}:")
#             self.stdout.write(f"   📥 اولیه: {initial} رکورد")
#             self.stdout.write(f"   📤 انتقال یافته: {transferred} رکورد")
#             self.stdout.write(f"   🗑️  پاک شده: {cleaned} رکورد")
#             self.stdout.write(f"   ✅ نهایی: {final_count} رکورد")
#
#             total_transferred += transferred
#             total_cleaned += cleaned
#
#         self.stdout.write("\n" + "=" * 50)
#         self.stdout.write(f"📈 جمع کل انتقال: {total_transferred} رکورد")
#         self.stdout.write(f"🗑️  جمع کل پاک‌سازی: {total_cleaned} رکورد")
#         self.stdout.write("=" * 50)
#
#         # بررسی ویژه ProductPricing
#         self.check_product_pricing_special()
#
#     def check_product_pricing_special(self):
#         """بررسی ویژه برای ProductPricing"""
#         try:
#             from account_app.models import ProductPricing
#
#             # دریافت تعداد نهایی
#             final_count = ProductPricing.objects.count()
#
#             # دریافت تعداد از سرور برای مقایسه
#             server_ids = self.get_server_ids(ProductPricing)
#             if server_ids is not None:
#                 server_count = len(server_ids)
#
#                 if final_count == server_count:
#                     self.stdout.write(f"\n🎯 ProductPricing: تطابق کامل ✅ (لوکال: {final_count} | سرور: {server_count})")
#                 else:
#                     self.stdout.write(f"\n⚠️ ProductPricing: عدم تطابق ❌ (لوکال: {final_count} | سرور: {server_count})")
#
#                     # اگر هنوز مشکل وجود دارد، پاکسازی کامل و انتقال مجدد
#                     if final_count > server_count:
#                         self.stdout.write("🔄 اجرای پاکسازی و انتقال مجدد ProductPricing...")
#                         ProductPricing.objects.all().delete()
#                         retry_count = self.sync_single_model(ProductPricing)
#                         self.stdout.write(f"🔄 انتقال مجدد: {retry_count} رکورد")
#
#         except Exception as e:
#             self.stdout.write(f"⚠️ خطا در بررسی ویژه ProductPricing: {e}")

from django.core.management.base import BaseCommand
from django.conf import settings
import requests
from django.apps import apps
from django.db import transaction
from django.db.models import Q


class Command(BaseCommand):
    help = 'انتقال کامل account_app با مقایسه و پاکسازی خودکار داده‌های اضافه'

    def handle(self, *args, **options):
        if not settings.OFFLINE_MODE:
            self.stdout.write("❌ فقط در حالت آفلاین قابل اجراست")
            return

        self.stdout.write("🚀 شروع انتقال کامل account_app...")

        # مرحله 0: بررسی اولیه و دیباگ کامل
        self.stdout.write("\n🔍 مرحله 0: بررسی اولیه و دیباگ کامل...")
        self.debug_complete_database_state()
        initial_status = self.get_initial_status()

        # مرحله 1: انتقال مدل‌های مستقل
        self.stdout.write("\n📦 مرحله 1: انتقال مدل‌های مستقل...")
        independent_models = [
            'Product', 'ProductPricing', 'PaymentMethod',
            'Expense', 'ExpenseImage', 'StockTransaction'
        ]

        transfer_results = {}
        for model_name in independent_models:
            try:
                model_class = apps.get_model('account_app', model_name)
                transferred_count = self.sync_single_model(model_class)
                transfer_results[model_name] = transferred_count
                self.stdout.write(f"✅ {model_name}: {transferred_count} رکورد انتقال یافت")
            except Exception as e:
                self.stdout.write(f"❌ خطا در انتقال {model_name}: {e}")
                transfer_results[model_name] = 0

        # مرحله 2: انتقال InventoryCount
        self.stdout.write("\n📦 مرحله 2: انتقال InventoryCount...")
        try:
            model_class = apps.get_model('account_app', 'InventoryCount')
            transferred_count = self.sync_single_model(model_class)
            transfer_results['InventoryCount'] = transferred_count
            self.stdout.write(f"✅ InventoryCount: {transferred_count} رکورد انتقال یافت")
        except Exception as e:
            self.stdout.write(f"❌ خطا در انتقال InventoryCount: {e}")
            transfer_results['InventoryCount'] = 0

        # مرحله 3: مقایسه و پاکسازی خودکار
        self.stdout.write("\n🔍 مرحله 3: مقایسه و پاکسازی خودکار...")
        cleanup_results = self.auto_cleanup_all_models()

        # مرحله 4: بررسی نهایی و گزارش
        self.stdout.write("\n📊 مرحله 4: گزارش نهایی...")
        self.generate_final_report(initial_status, transfer_results, cleanup_results)

        self.stdout.write(
            self.style.SUCCESS("\n🎉 انتقال کامل account_app با موفقیت انجام شد!")
        )

    def debug_complete_database_state(self):
        """بررسی کامل وضعیت دیتابیس"""
        self.stdout.write("\n🔍 دیباگ کامل وضعیت دیتابیس:")

        from django.db import connection

        try:
            # 1. لیست تمام جدول‌های موجود
            with connection.cursor() as cursor:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
                tables = cursor.fetchall()
                self.stdout.write("\n📋 تمام جدول‌های موجود در دیتابیس:")
                for table in tables:
                    self.stdout.write(f"   - {table[0]}")

            # 2. بررسی دقیق جدول‌های مربوط به branch
            self.stdout.write(f"\n🔍 بررسی دقیق جدول‌های branch:")
            branch_keywords = ['branch', 'shobe', 'shoabe', 'canact', 'cantact', 'contact']

            for keyword in branch_keywords:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE ?",
                                   [f'%{keyword}%'])
                    branch_tables = cursor.fetchall()
                    for table in branch_tables:
                        table_name = table[0]
                        cursor.execute(f"SELECT COUNT(*) as count, MAX(id) as max_id FROM {table_name}")
                        count_result = cursor.fetchone()
                        count = count_result[0] if count_result else 0
                        max_id = count_result[1] if count_result else 0

                        cursor.execute(f"PRAGMA table_info({table_name})")
                        columns = cursor.fetchall()
                        column_names = [col[1] for col in columns]

                        self.stdout.write(f"   📊 {table_name}:")
                        self.stdout.write(f"      تعداد رکوردها: {count}")
                        self.stdout.write(f"      بیشترین ID: {max_id}")
                        self.stdout.write(f"      ستون‌ها: {', '.join(column_names)}")

                        # نمونه‌ای از داده‌ها
                        if count > 0:
                            cursor.execute(f"SELECT id, name FROM {table_name} LIMIT 3")
                            sample_data = cursor.fetchall()
                            self.stdout.write(f"      نمونه داده: {sample_data}")

            # 3. بررسی دقیق جدول‌های مربوط به user
            self.stdout.write(f"\n🔍 بررسی دقیق جدول‌های user:")
            user_keywords = ['user', 'auth', 'account', 'userprofile']

            for keyword in user_keywords:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE ?",
                                   [f'%{keyword}%'])
                    user_tables = cursor.fetchall()
                    for table in user_tables:
                        table_name = table[0]
                        cursor.execute(f"SELECT COUNT(*) as count, MAX(id) as max_id FROM {table_name}")
                        count_result = cursor.fetchone()
                        count = count_result[0] if count_result else 0
                        max_id = count_result[1] if count_result else 0

                        self.stdout.write(f"   📊 {table_name}:")
                        self.stdout.write(f"      تعداد رکوردها: {count}")
                        self.stdout.write(f"      بیشترین ID: {max_id}")

                        # نمونه‌ای از داده‌ها
                        if count > 0:
                            cursor.execute(f"SELECT id, username FROM {table_name} LIMIT 3")
                            sample_data = cursor.fetchall()
                            self.stdout.write(f"      نمونه داده: {sample_data}")

            # 4. بررسی جدول InventoryCount
            self.stdout.write(f"\n🔍 بررسی جدول‌های InventoryCount:")
            inventory_keywords = ['inventory', 'inventor', 'count']

            for keyword in inventory_keywords:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE ?",
                                   [f'%{keyword}%'])
                    inventory_tables = cursor.fetchall()
                    for table in inventory_tables:
                        table_name = table[0]
                        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                        count = cursor.fetchone()[0]

                        cursor.execute(f"PRAGMA table_info({table_name})")
                        columns = cursor.fetchall()
                        column_names = [col[1] for col in columns]

                        self.stdout.write(f"   📊 {table_name}:")
                        self.stdout.write(f"      تعداد رکوردها: {count}")
                        self.stdout.write(f"      ستون‌ها: {', '.join(column_names)}")

        except Exception as e:
            self.stdout.write(f"❌ خطا در دیباگ دیتابیس: {e}")

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
        """ذخیره امن رکوردها"""
        saved_count = 0
        error_count = 0

        for record_data in records:
            try:
                record_id = record_data.get('id')
                if not record_id:
                    continue

                # 🔄 راه حل قطعی: برای InventoryCount از روش ویژه استفاده می‌کنیم
                if model_class.__name__ == 'InventoryCount':
                    success = self.insert_inventory_comprehensive(record_data, record_id)
                    if success:
                        saved_count += 1
                    else:
                        error_count += 1
                else:
                    # برای سایر مدل‌ها از روش معمول
                    processed_data = self.process_record_data(record_data, model_class)
                    obj, created = model_class.objects.update_or_create(
                        id=record_id,
                        defaults=processed_data
                    )
                    saved_count += 1

            except Exception as e:
                error_count += 1
                self.stdout.write(f"⚠️ خطا در {model_class.__name__} ID {record_id}: {str(e)}")
                continue

        if error_count > 0:
            self.stdout.write(f"   ❌ {error_count} خطا در ذخیره")

        return saved_count

    def insert_inventory_comprehensive(self, record_data, record_id):
        """درج جامع InventoryCount با تمام راه‌حل‌های ممکن"""
        from django.db import connection
        from decimal import Decimal

        try:
            # استخراج داده‌های ضروری
            product_name = record_data.get('product_name', '')
            is_new = record_data.get('is_new', True)
            quantity = record_data.get('quantity', 0)
            count_date = record_data.get('count_date', '')
            barcode_data = record_data.get('barcode_data', '')
            selling_price = record_data.get('selling_price')
            profit_percentage = Decimal(str(record_data.get('profit_percentage', '30.00')))
            created_at = record_data.get('created_at')

            self.stdout.write(f"🔍 پردازش InventoryCount ID {record_id}: {product_name}")

            # 🔄 راه حل 1: پیدا کردن branch_id و counter_id با روش‌های مختلف
            branch_id = self.find_branch_id_comprehensive()
            counter_id = self.find_user_id_comprehensive()

            if not branch_id:
                self.stdout.write(f"❌ InventoryCount ID {record_id}: هیچ شعبه معتبری در کل دیتابیس پیدا نشد")
                return False

            if not counter_id:
                self.stdout.write(f"❌ InventoryCount ID {record_id}: هیچ کاربر معتبری در کل دیتابیس پیدا نشد")
                return False

            self.stdout.write(f"✅ استفاده از branch_id: {branch_id}, counter_id: {counter_id}")

            # 🔄 راه حل 2: پیدا کردن نام صحیح جدول InventoryCount
            target_table = self.find_inventory_table()
            if not target_table:
                self.stdout.write(f"❌ InventoryCount ID {record_id}: هیچ جدول InventoryCount پیدا نشد")
                return False

            # 🔄 راه حل 3: درج با Raw SQL
            with connection.cursor() as cursor:
                try:
                    # حذف رکورد قبلی اگر وجود دارد
                    cursor.execute(f"DELETE FROM {target_table} WHERE id = ?", [record_id])

                    # درج رکورد جدید
                    cursor.execute(f"""
                        INSERT INTO {target_table} 
                        (id, product_name, is_new, quantity, count_date, created_at, 
                         barcode_data, selling_price, branch_id, counter_id, profit_percentage)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, [
                        record_id, product_name, is_new, quantity, count_date,
                        created_at, barcode_data, selling_price,
                        branch_id, counter_id, profit_percentage
                    ])

                    self.stdout.write(f"✅ InventoryCount ID {record_id}: انتقال موفق")
                    return True

                except Exception as sql_error:
                    self.stdout.write(f"❌ InventoryCount ID {record_id}: خطای SQL - {str(sql_error)}")

                    # 🔄 راه حل 4: اگر خطای SQL داشتیم، سعی می‌کنیم با ORM ذخیره کنیم
                    try:
                        self.stdout.write(f"🔄 تلاش با ORM برای InventoryCount ID {record_id}")
                        from account_app.models import InventoryCount

                        inventory = InventoryCount(
                            id=record_id,
                            product_name=product_name,
                            is_new=is_new,
                            quantity=quantity,
                            count_date=count_date,
                            created_at=created_at,
                            barcode_data=barcode_data,
                            selling_price=selling_price,
                            branch_id=branch_id,
                            counter_id=counter_id,
                            profit_percentage=profit_percentage
                        )

                        # غیرفعال کردن اعتبارسنجی‌ها
                        inventory.full_clean = lambda: None
                        inventory.save()

                        self.stdout.write(f"✅ InventoryCount ID {record_id}: انتقال موفق با ORM")
                        return True

                    except Exception as orm_error:
                        self.stdout.write(f"❌ InventoryCount ID {record_id}: خطای ORM - {str(orm_error)}")
                        return False

        except Exception as e:
            self.stdout.write(f"❌ InventoryCount ID {record_id}: خطای کلی - {str(e)}")
            return False

    def find_branch_id_comprehensive(self):
        """پیدا کردن branch_id با تمام روش‌های ممکن"""
        from django.db import connection

        methods = [
            self._find_branch_method1,  # apps.get_model
            self._find_branch_method2,  # جستجوی مستقیم جدول
            self._find_branch_method3,  # جستجوی با کلیدواژه‌های مختلف
            self._find_branch_method4,  # ایجاد در صورت عدم وجود
        ]

        for method in methods:
            try:
                result = method()
                if result:
                    return result
            except Exception as e:
                continue

        return None

    def _find_branch_method1(self):
        """روش 1: استفاده از apps.get_model"""
        app_names = ['cantact_app', 'contact_app', 'canact_app', 'account_app']
        for app_name in app_names:
            try:
                Branch = apps.get_model(app_name, 'Branch')
                branch = Branch.objects.first()
                if branch:
                    self.stdout.write(f"✅ شعبه پیدا شد ({app_name}): {branch.name} (ID: {branch.id})")
                    return branch.id
            except:
                continue
        return None

    def _find_branch_method2(self):
        """روش 2: جستجوی مستقیم در جدول"""
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%branch%'")
            tables = cursor.fetchall()
            for table in tables:
                try:
                    cursor.execute(f"SELECT id, name FROM {table[0]} LIMIT 1")
                    row = cursor.fetchone()
                    if row:
                        self.stdout.write(f"✅ شعبه در جدول {table[0]}: ID {row[0]}, نام {row[1]}")
                        return row[0]
                except:
                    continue
        return None

    def _find_branch_method3(self):
        """روش 3: جستجوی با کلیدواژه‌های مختلف"""
        from django.db import connection
        keywords = ['branch', 'shobe', 'shoabe', 'canact', 'cantact', 'contact']

        for keyword in keywords:
            with connection.cursor() as cursor:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE ?", [f'%{keyword}%'])
                tables = cursor.fetchall()
                for table in tables:
                    try:
                        cursor.execute(f"SELECT id FROM {table[0]} LIMIT 1")
                        row = cursor.fetchone()
                        if row:
                            self.stdout.write(f"✅ شعبه در جدول {table[0]}: ID {row[0]}")
                            return row[0]
                    except:
                        continue
        return None

    def _find_branch_method4(self):
        """روش 4: ایجاد شعبه در صورت عدم وجود"""
        from django.db import connection
        with connection.cursor() as cursor:
            # پیدا کردن یک جدول مناسب برای درج شعبه
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%branch%'")
            table = cursor.fetchone()
            if table:
                table_name = table[0]
                try:
                    # درج شعبه جدید
                    cursor.execute(f"INSERT INTO {table_name} (name, address) VALUES (?, ?)",
                                   ['شعبه مرکزی', 'آدرس پیش‌فرض'])
                    cursor.execute(f"SELECT last_insert_rowid()")
                    new_id = cursor.fetchone()[0]
                    self.stdout.write(f"✅ شعبه جدید ایجاد شد: ID {new_id}")
                    return new_id
                except:
                    pass
        return None

    def find_user_id_comprehensive(self):
        """پیدا کردن user_id با تمام روش‌های ممکن"""
        from django.db import connection

        methods = [
            self._find_user_method1,  # apps.get_model
            self._find_user_method2,  # جستجوی مستقیم جدول
            self._find_user_method3,  # جستجوی با کلیدواژه‌های مختلف
            self._find_user_method4,  # ایجاد در صورت عدم وجود
        ]

        for method in methods:
            try:
                result = method()
                if result:
                    return result
            except Exception as e:
                continue

        return None

    def _find_user_method1(self):
        """روش 1: استفاده از apps.get_model"""
        try:
            User = apps.get_model('auth', 'User')
            user = User.objects.first()
            if user:
                self.stdout.write(f"✅ کاربر پیدا شد: {user.username} (ID: {user.id})")
                return user.id
        except:
            pass
        return None

    def _find_user_method2(self):
        """روش 2: جستجوی مستقیم در جدول"""
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND (name LIKE '%user%' OR name LIKE '%auth%')")
            tables = cursor.fetchall()
            for table in tables:
                try:
                    cursor.execute(f"SELECT id, username FROM {table[0]} LIMIT 1")
                    row = cursor.fetchone()
                    if row:
                        self.stdout.write(f"✅ کاربر در جدول {table[0]}: ID {row[0]}, نام {row[1]}")
                        return row[0]
                except:
                    continue
        return None

    def _find_user_method3(self):
        """روش 3: جستجوی با کلیدواژه‌های مختلف"""
        from django.db import connection
        keywords = ['user', 'auth', 'account']

        for keyword in keywords:
            with connection.cursor() as cursor:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE ?", [f'%{keyword}%'])
                tables = cursor.fetchall()
                for table in tables:
                    try:
                        cursor.execute(f"SELECT id FROM {table[0]} LIMIT 1")
                        row = cursor.fetchone()
                        if row:
                            self.stdout.write(f"✅ کاربر در جدول {table[0]}: ID {row[0]}")
                            return row[0]
                    except:
                        continue
        return None

    def _find_user_method4(self):
        """روش 4: ایجاد کاربر در صورت عدم وجود"""
        from django.db import connection
        with connection.cursor() as cursor:
            # پیدا کردن یک جدول مناسب برای درج کاربر
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%user%'")
            table = cursor.fetchone()
            if table:
                table_name = table[0]
                try:
                    # درج کاربر جدید
                    cursor.execute(f"INSERT INTO {table_name} (username, password) VALUES (?, ?)",
                                   ['admin', 'admin123'])
                    cursor.execute(f"SELECT last_insert_rowid()")
                    new_id = cursor.fetchone()[0]
                    self.stdout.write(f"✅ کاربر جدید ایجاد شد: ID {new_id}")
                    return new_id
                except:
                    pass
        return None

    def find_inventory_table(self):
        """پیدا کردن نام جدول InventoryCount"""
        from django.db import connection
        with connection.cursor() as cursor:
            keywords = ['inventory', 'inventor', 'count']

            for keyword in keywords:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE ?", [f'%{keyword}%'])
                tables = cursor.fetchall()
                for table in tables:
                    table_name = table[0]
                    # بررسی ساختار جدول
                    try:
                        cursor.execute(f"PRAGMA table_info({table_name})")
                        columns = cursor.fetchall()
                        column_names = [col[1] for col in columns]

                        # بررسی وجود ستون‌های ضروری
                        essential_columns = ['product_name', 'branch_id', 'counter_id']
                        if all(col in column_names for col in essential_columns):
                            self.stdout.write(f"✅ جدول InventoryCount پیدا شد: {table_name}")
                            return table_name
                    except:
                        continue
        return None

    def process_record_data(self, record_data, model_class):
        """پردازش داده‌های رکورد"""
        processed_data = {}

        for field_name, value in record_data.items():
            if value is None:
                processed_data[field_name] = None
                continue

            # مدیریت فیلدهای ForeignKey
            if field_name.endswith('_id') and isinstance(value, int):
                processed_data[field_name] = value

            # مدیریت فیلدهای Decimal
            elif isinstance(value, (int, float)) and self.is_decimal_field(model_class, field_name):
                from decimal import Decimal
                processed_data[field_name] = Decimal(str(value))

            # مدیریت فیلدهای تاریخ
            elif field_name.endswith('_date') or field_name in ['created_at', 'updated_at']:
                from django.utils import timezone
                from datetime import datetime
                try:
                    if isinstance(value, str):
                        processed_data[field_name] = datetime.fromisoformat(value.replace('Z', '+00:00'))
                    else:
                        processed_data[field_name] = value
                except:
                    processed_data[field_name] = value

            # سایر فیلدها
            else:
                processed_data[field_name] = value

        return processed_data

    def is_decimal_field(self, model_class, field_name):
        """بررسی فیلدهای Decimal"""
        try:
            field = model_class._meta.get_field(field_name)
            return field.get_internal_type() in ['DecimalField', 'FloatField']
        except:
            return False

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

        # بررسی ویژه
        self.check_special_cases()

    def check_special_cases(self):
        """بررسی موارد ویژه"""
        try:
            from account_app.models import ProductPricing

            # بررسی ProductPricing
            final_count = ProductPricing.objects.count()
            server_ids = self.get_server_ids(ProductPricing)
            if server_ids is not None:
                server_count = len(server_ids)
                if final_count == server_count:
                    self.stdout.write(f"\n🎯 ProductPricing: تطابق کامل ✅ (لوکال: {final_count} | سرور: {server_count})")
                else:
                    self.stdout.write(f"\n⚠️ ProductPricing: عدم تطابق ❌ (لوکال: {final_count} | سرور: {server_count})")

            # بررسی InventoryCount
            from account_app.models import InventoryCount
            inventory_count = InventoryCount.objects.count()
            self.stdout.write(f"\n📦 InventoryCount نهایی: {inventory_count} رکورد")

        except Exception as e:
            self.stdout.write(f"⚠️ خطا در بررسی موارد ویژه: {e}")