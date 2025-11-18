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
from django.contrib.auth import get_user_model
from django.db import connection


class Command(BaseCommand):
    help = 'انتقال کامل account_app با مدیریت وابستگی‌ها و خطاها'

    def handle(self, *args, **options):
        if not settings.OFFLINE_MODE:
            self.stdout.write("❌ فقط در حالت آفلاین قابل اجراست")
            return

        self.stdout.write("🚀 شروع انتقال کامل account_app...")

        # مرحله 0: بررسی اولیه و آماده‌سازی
        self.stdout.write("\n🔍 مرحله 0: بررسی اولیه و آماده‌سازی...")
        self.debug_initial_state()
        initial_status = self.get_initial_status()

        # مرحله 1: انتقال مدل‌های مستقل
        self.stdout.write("\n📦 مرحله 1: انتقال مدل‌های مستقل...")
        independent_models = ['Product', 'ProductPricing', 'PaymentMethod']

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

        # مرحله 2: انتقال مدل‌های با وابستگی متوسط
        self.stdout.write("\n📦 مرحله 2: انتقال مدل‌های با وابستگی...")
        dependent_models = ['Expense', 'ExpenseImage', 'StockTransaction']

        for model_name in dependent_models:
            try:
                model_class = apps.get_model('account_app', model_name)
                transferred_count = self.sync_single_model(model_class)
                transfer_results[model_name] = transferred_count
                self.stdout.write(f"✅ {model_name}: {transferred_count} رکورد انتقال یافت")
            except Exception as e:
                self.stdout.write(f"❌ خطا در انتقال {model_name}: {e}")
                transfer_results[model_name] = 0

        # مرحله 3: انتقال InventoryCount با روش ویژه
        self.stdout.write("\n📦 مرحله 3: انتقال InventoryCount...")
        try:
            model_class = apps.get_model('account_app', 'InventoryCount')
            transferred_count = self.sync_inventory_count_special(model_class)
            transfer_results['InventoryCount'] = transferred_count
            self.stdout.write(f"✅ InventoryCount: {transferred_count} رکورد انتقال یافت")
        except Exception as e:
            self.stdout.write(f"❌ خطا در انتقال InventoryCount: {e}")
            transfer_results['InventoryCount'] = 0

        # مرحله 4: پاکسازی و گزارش
        self.stdout.write("\n🔍 مرحله 4: پاکسازی و گزارش...")
        cleanup_results = self.auto_cleanup_all_models()
        self.generate_final_report(initial_status, transfer_results, cleanup_results)

        self.stdout.write(
            self.style.SUCCESS("\n🎉 انتقال کامل account_app با موفقیت انجام شد!")
        )

    def debug_initial_state(self):
        """بررسی وضعیت اولیه سیستم"""
        self.stdout.write("🔍 بررسی وضعیت اولیه...")

        # بررسی کاربران
        try:
            User = get_user_model()
            user_count = User.objects.count()
            self.stdout.write(f"   👤 کاربران: {user_count} رکورد")
            if user_count == 0:
                self.stdout.write("   ⚠️ هیچ کاربری در سیستم وجود ندارد")
        except Exception as e:
            self.stdout.write(f"   ❌ خطا در بررسی کاربران: {e}")

        # بررسی شعبه‌ها
        try:
            from cantact_app.models import Branch
            branch_count = Branch.objects.count()
            self.stdout.write(f"   🏢 شعبه‌ها: {branch_count} رکورد")
            if branch_count == 0:
                self.stdout.write("   ⚠️ هیچ شعبه‌ای در سیستم وجود ندارد")
        except Exception as e:
            self.stdout.write(f"   ❌ خطا در بررسی شعبه‌ها: {e}")

        # بررسی تنظیمات
        self.stdout.write(f"   🌐 آدرس سرور: {getattr(settings, 'ONLINE_SERVER_URL', 'Not set')}")

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
        try:
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
                else:
                    self.stdout.write(
                        f"⚠️ خطا در پاسخ سرور برای {model_class.__name__}: {data.get('message', 'Unknown error')}")
            else:
                self.stdout.write(f"⚠️ خطای HTTP {response.status_code} برای {model_class.__name__}")

        except requests.exceptions.RequestException as e:
            self.stdout.write(f"❌ خطای شبکه برای {model_class.__name__}: {e}")
        except Exception as e:
            self.stdout.write(f"❌ خطای غیرمنتظره برای {model_class.__name__}: {e}")

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

                # پردازش داده‌ها
                processed_data = self.process_record_data(record_data, model_class)

                # مدیریت ویژه برای مدل‌های خاص
                if model_class.__name__ in ['Expense', 'StockTransaction']:
                    processed_data = self.fix_dependencies(processed_data, model_class)

                # ایجاد یا آپدیت
                obj, created = model_class.objects.update_or_create(
                    id=record_id,
                    defaults=processed_data
                )
                saved_count += 1

                if saved_count % 100 == 0:
                    self.stdout.write(f"   📝 {saved_count} رکورد پردازش شد...")

            except Exception as e:
                error_count += 1
                if error_count <= 5:  # فقط ۵ خطای اول را نمایش بده
                    self.stdout.write(f"⚠️ خطا در {model_class.__name__} ID {record_id}: {str(e)}")
                continue

        if error_count > 0:
            self.stdout.write(f"   ❌ {error_count} خطا در ذخیره")

        return saved_count

    def sync_inventory_count_special(self, model_class):
        """انتقال ویژه InventoryCount"""
        try:
            response = requests.get(
                f"{settings.ONLINE_SERVER_URL}/api/sync/model-data/",
                params={'app': 'account_app', 'model': 'InventoryCount'},
                timeout=60
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    records = data.get('records', [])
                    self.stdout.write(f"📥 دریافت {len(records)} رکورد InventoryCount از سرور")

                    saved_count = 0
                    error_count = 0

                    for record_data in records:
                        success = self.insert_inventory_safe(record_data)
                        if success:
                            saved_count += 1
                        else:
                            error_count += 1

                        if (saved_count + error_count) % 100 == 0:
                            self.stdout.write(f"   📊 پردازش {saved_count + error_count} از {len(records)}...")

                    self.stdout.write(f"   ✅ {saved_count} موفق, ❌ {error_count} خطا")
                    return saved_count

        except Exception as e:
            self.stdout.write(f"❌ خطا در دریافت InventoryCount: {e}")

        return 0

    def insert_inventory_safe(self, record_data):
        """درج امن InventoryCount"""
        from decimal import Decimal
        import math

        try:
            record_id = record_data.get('id')
            if not record_id:
                return False

            # استخراج داده‌های ضروری
            product_name = record_data.get('product_name', '')
            is_new = record_data.get('is_new', True)
            quantity = record_data.get('quantity', 0)
            count_date = record_data.get('count_date', '')
            barcode_data = record_data.get('barcode_data', '')
            selling_price = record_data.get('selling_price')
            profit_percentage = Decimal(str(record_data.get('profit_percentage', '30.00')))
            created_at = record_data.get('created_at')

            # پیدا کردن branch_id و counter_id معتبر
            branch_id = self.get_valid_branch_id()
            counter_id = self.get_valid_user_id()

            if not branch_id or not counter_id:
                self.stdout.write(f"   ❌ InventoryCount {record_id}: وابستگی‌های ضروری پیدا نشد")
                return False

            # استفاده از Raw SQL برای درج قطعی
            with connection.cursor() as cursor:
                # حذف رکورد قبلی اگر وجود دارد
                cursor.execute("DELETE FROM account_app_inventorycount WHERE id = ?", [record_id])

                # درج رکورد جدید
                cursor.execute("""
                    INSERT INTO account_app_inventorycount 
                    (id, product_name, is_new, quantity, count_date, created_at, 
                     barcode_data, selling_price, branch_id, counter_id, profit_percentage)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    record_id, product_name, is_new, quantity, count_date,
                    created_at, barcode_data, selling_price,
                    branch_id, counter_id, profit_percentage
                ])

            return True

        except Exception as e:
            self.stdout.write(f"❌ خطا در InventoryCount ID {record_id}: {str(e)}")
            return False

    def get_valid_branch_id(self):
        """دریافت یک branch_id معتبر"""
        try:
            from cantact_app.models import Branch
            branch = Branch.objects.first()
            if branch:
                return branch.id
        except:
            pass

        # اگر پیدا نشد، از کوئری مستقیم استفاده کن
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id FROM cantact_app_branch LIMIT 1")
                row = cursor.fetchone()
                if row:
                    return row[0]
        except:
            pass

        return 1  # مقدار پیش‌فرض

    def get_valid_user_id(self):
        """دریافت یک user_id معتبر"""
        try:
            User = get_user_model()
            user = User.objects.first()
            if user:
                return user.id
        except:
            pass

        # اگر پیدا نشد، از کوئری مستقیم استفاده کن
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id FROM auth_user LIMIT 1")
                row = cursor.fetchone()
                if row:
                    return row[0]
        except:
            pass

        return 1  # مقدار پیش‌فرض

    def fix_dependencies(self, processed_data, model_class):
        """رفع مشکلات وابستگی برای مدل‌های خاص"""
        fixed_data = processed_data.copy()

        # برای Expense
        if model_class.__name__ == 'Expense':
            if 'branch_id' in fixed_data and not self.check_branch_exists(fixed_data['branch_id']):
                fixed_data['branch_id'] = self.get_valid_branch_id()

            if 'user_id' in fixed_data and not self.check_user_exists(fixed_data['user_id']):
                fixed_data['user_id'] = self.get_valid_user_id()

        # برای StockTransaction
        elif model_class.__name__ == 'StockTransaction':
            if 'user_id' in fixed_data and not self.check_user_exists(fixed_data['user_id']):
                fixed_data['user_id'] = self.get_valid_user_id()

        return fixed_data

    def check_branch_exists(self, branch_id):
        """بررسی وجود شعبه"""
        try:
            from cantact_app.models import Branch
            return Branch.objects.filter(id=branch_id).exists()
        except:
            return False

    def check_user_exists(self, user_id):
        """بررسی وجود کاربر"""
        try:
            User = get_user_model()
            return User.objects.filter(id=user_id).exists()
        except:
            return False

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
            from account_app.models import ProductPricing, InventoryCount

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
            inventory_count = InventoryCount.objects.count()
            server_ids = self.get_server_ids(InventoryCount)
            if server_ids is not None:
                server_count = len(server_ids)
                if inventory_count == server_count:
                    self.stdout.write(
                        f"🎯 InventoryCount: تطابق کامل ✅ (لوکال: {inventory_count} | سرور: {server_count})")
                else:
                    self.stdout.write(
                        f"⚠️ InventoryCount: عدم تطابق ❌ (لوکال: {inventory_count} | سرور: {server_count})")

        except Exception as e:
            self.stdout.write(f"⚠️ خطا در بررسی موارد ویژه: {e}")