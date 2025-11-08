#
# from django.core.management.base import BaseCommand
# from django.conf import settings
# import requests
# from django.apps import apps
# from django.db import transaction
#
#
# class Command(BaseCommand):
#     help = 'انتقال کامل account_app با مدیریت وابستگی‌ها'
#
#     def handle(self, *args, **options):
#         if not settings.OFFLINE_MODE:
#             self.stdout.write("❌ فقط در حالت آفلاین قابل اجراست")
#             return
#
#         self.stdout.write("🚀 شروع انتقال کامل account_app با مدیریت وابستگی‌ها...")
#
#         # مرحله 1: انتقال مدل‌های مستقل
#         self.stdout.write("\n📦 مرحله 1: انتقال مدل‌های مستقل...")
#         independent_models = ['Product', 'ProductPricing', 'PaymentMethod']
#         self.sync_models(independent_models)
#
#         # مرحله 2: انتقال مدل‌های با وابستگی داخلی
#         self.stdout.write("\n📦 مرحله 2: انتقال مدل‌های با وابستگی داخلی...")
#         dependent_models = ['Expense', 'ExpenseImage', 'StockTransaction']
#         self.sync_models(dependent_models)
#
#         # مرحله 3: انتقال InventoryCount با مدیریت ویژه
#         self.stdout.write("\n📦 مرحله 3: انتقال InventoryCount...")
#         self.sync_inventory_count()
#
#         self.stdout.write(
#             self.style.SUCCESS("\n🎉 انتقال کامل account_app با موفقیت انجام شد!")
#         )
#
#     def sync_models(self, model_names):
#         """انتقال گروهی از مدل‌ها"""
#         for model_name in model_names:
#             try:
#                 model_class = apps.get_model('account_app', model_name)
#                 count = self.sync_model_with_retry(model_class)
#                 self.stdout.write(f"✅ {model_name}: {count} رکورد")
#             except Exception as e:
#                 self.stdout.write(f"❌ خطا در {model_name}: {e}")
#
#     def sync_model_with_retry(self, model_class, max_retries=3):
#         """انتقال یک مدل با قابلیت تکرار در صورت خطا"""
#         for attempt in range(max_retries):
#             try:
#                 return self.sync_single_model(model_class)
#             except Exception as e:
#                 if attempt == max_retries - 1:
#                     raise e
#                 self.stdout.write(f"⚠️ تلاش مجدد {attempt + 1} برای {model_class.__name__}")
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
#                 return self.save_records_safe(model_class, records)
#         return 0
#
#     def save_records_safe(self, model_class, records):
#         """ذخیره امن رکوردها با مدیریت خطاهای وابستگی"""
#         saved_count = 0
#
#         for record_data in records:
#             try:
#                 record_id = record_data.get('id')
#                 if not record_id:
#                     continue
#
#                 # پردازش داده‌ها با مدیریت ویژه برای فیلدهای وابسته
#                 processed_data = self.process_with_dependency_check(record_data, model_class)
#
#                 # ایجاد یا آپدیت
#                 obj, created = model_class.objects.update_or_create(
#                     id=record_id,
#                     defaults=processed_data
#                 )
#                 saved_count += 1
#
#             except Exception as e:
#                 error_msg = str(e)
#                 if "FOREIGN KEY" in error_msg:
#                     # خطای وابستگی - ایجاد رکورد با مقادیر پیش‌فرض برای فیلدهای وابسته
#                     saved_count += self.handle_foreign_key_error(model_class, record_data, record_id, error_msg)
#                 else:
#                     self.stdout.write(f"⚠️ خطا در ذخیره رکورد {record_id}: {e}")
#                 continue
#
#         return saved_count
#
#     def process_with_dependency_check(self, record_data, model_class):
#         """پردازش داده‌ها با بررسی وابستگی‌ها"""
#         processed_data = {}
#
#         for field_name, value in record_data.items():
#             if value is None:
#                 processed_data[field_name] = None
#                 continue
#
#             # مدیریت فیلدهای ForeignKey
#             if field_name.endswith('_id') and isinstance(value, int):
#                 if self.check_foreign_key_exists(field_name, value):
#                     processed_data[field_name] = value
#                 else:
#                     # اگر وابستگی وجود ندارد، از مقدار پیش‌فرض استفاده کن
#                     processed_data[field_name] = self.get_default_foreign_key(field_name)
#
#             # مدیریت فیلدهای Decimal
#             elif isinstance(value, (int, float)) and self.is_decimal_field(model_class, field_name):
#                 from decimal import Decimal
#                 processed_data[field_name] = Decimal(str(value))
#
#             # سایر فیلدها
#             else:
#                 processed_data[field_name] = value
#
#         return processed_data
#
#     def check_foreign_key_exists(self, field_name, value):
#         """بررسی وجود رکورد وابسته"""
#         try:
#             # استخراج نام مدل از فیلد (مثلاً branch_id -> Branch)
#             model_name = field_name.replace('_id', '').title()
#             model_class = apps.get_model('cantact_app', model_name)
#             return model_class.objects.filter(id=value).exists()
#         except:
#             try:
#                 # اگر در cantact_app نبود، در auth بررسی کن
#                 if field_name in ['counter_id', 'user_id']:
#                     from django.contrib.auth.models import User
#                     return User.objects.filter(id=value).exists()
#             except:
#                 pass
#         return False
#
#     def get_default_foreign_key(self, field_name):
#         """دریافت مقدار پیش‌فرض برای فیلدهای وابسته"""
#         try:
#             if field_name == 'branch_id':
#                 from cantact_app.models import Branch
#                 default_branch = Branch.objects.first()
#                 return default_branch.id if default_branch else 1
#             elif field_name in ['counter_id', 'user_id']:
#                 from django.contrib.auth.models import User
#                 default_user = User.objects.first()
#                 return default_user.id if default_user else 1
#         except:
#             pass
#         return 1  # مقدار پیش‌فرض
#
#     def sync_inventory_count(self):
#         """انتقال ویژه InventoryCount"""
#         try:
#             model_class = apps.get_model('account_app', 'InventoryCount')
#
#             # دریافت تمام رکوردها
#             response = requests.get(
#                 f"{settings.ONLINE_SERVER_URL}/api/sync/model-data/",
#                 params={'app': 'account_app', 'model': 'InventoryCount'},
#                 timeout=60
#             )
#
#             if response.status_code == 200:
#                 data = response.json()
#                 if data.get('status') == 'success':
#                     records = data.get('records', [])
#
#                     self.stdout.write(f"📊 تعداد رکوردهای InventoryCount در سرور: {len(records)}")
#
#                     saved_count = 0
#                     for record_data in records:
#                         try:
#                             record_id = record_data.get('id')
#                             if not record_id:
#                                 continue
#
#                             # پردازش ویژه برای InventoryCount
#                             processed_data = self.process_inventory_data(record_data)
#
#                             with transaction.atomic():
#                                 obj, created = model_class.objects.update_or_create(
#                                     id=record_id,
#                                     defaults=processed_data
#                                 )
#                                 saved_count += 1
#
#                                 if saved_count % 100 == 0:
#                                     self.stdout.write(f"📝 {saved_count} رکورد InventoryCount پردازش شد...")
#
#                         except Exception as e:
#                             self.stdout.write(f"⚠️ خطا در InventoryCount {record_id}: {e}")
#                             continue
#
#                     self.stdout.write(f"✅ InventoryCount: {saved_count} رکورد")
#                     return saved_count
#
#             return 0
#
#         except Exception as e:
#             self.stdout.write(f"❌ خطا در انتقال InventoryCount: {e}")
#             return 0
#
#     def process_inventory_data(self, record_data):
#         """پردازش ویژه داده‌های InventoryCount"""
#         processed_data = {}
#
#         # فیلدهای اصلی
#         inventory_fields = [
#             'product_name', 'is_new', 'quantity', 'count_date',
#             'created_at', 'barcode_data', 'selling_price', 'profit_percentage'
#         ]
#
#         for field in inventory_fields:
#             if field in record_data:
#                 value = record_data[field]
#                 if value is not None:
#                     if field in ['selling_price', 'profit_percentage']:
#                         from decimal import Decimal
#                         processed_data[field] = Decimal(str(value))
#                     else:
#                         processed_data[field] = value
#
#         # مدیریت فیلدهای وابسته
#         branch_id = record_data.get('branch_id')
#         counter_id = record_data.get('counter_id')
#
#         processed_data['branch_id'] = self.get_default_foreign_key('branch_id') if not self.check_foreign_key_exists(
#             'branch_id', branch_id) else branch_id
#         processed_data['counter_id'] = self.get_default_foreign_key('counter_id') if not self.check_foreign_key_exists(
#             'counter_id', counter_id) else counter_id
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
#     def handle_foreign_key_error(self, model_class, record_data, record_id, error_msg):
#         """مدیریت خطاهای وابستگی"""
#         try:
#             # برای InventoryCount، با مقادیر پیش‌فرض ذخیره کن
#             if model_class.__name__ == 'InventoryCount':
#                 processed_data = self.process_inventory_data(record_data)
#                 obj, created = model_class.objects.update_or_create(
#                     id=record_id,
#                     defaults=processed_data
#                 )
#                 return 1
#         except Exception as e:
#             self.stdout.write(f"⚠️ خطا در مدیریت وابستگی برای {record_id}: {e}")
#
#         return 0

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
        """ذخیره امن رکوردها با جلوگیری از تکراری"""
        saved_count = 0
        duplicate_count = 0
        error_count = 0

        for record_data in records:
            try:
                record_id = record_data.get('id')
                if not record_id:
                    continue

                # جلوگیری از رکوردهای تکراری
                if model_class.objects.filter(id=record_id).exists():
                    duplicate_count += 1
                    continue

                # پردازش داده‌ها
                processed_data = self.process_record_data(record_data, model_class)

                # ایجاد یا آپدیت
                obj, created = model_class.objects.update_or_create(
                    id=record_id,
                    defaults=processed_data
                )
                saved_count += 1

            except Exception as e:
                error_count += 1
                continue

        if duplicate_count > 0:
            self.stdout.write(f"   ⏭️ {duplicate_count} رکورد تکراری رد شد")
        if error_count > 0:
            self.stdout.write(f"   ❌ {error_count} خطا در ذخیره")

        return saved_count

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

        # بررسی ویژه ProductPricing
        self.check_product_pricing_special()

    def check_product_pricing_special(self):
        """بررسی ویژه برای ProductPricing"""
        try:
            from account_app.models import ProductPricing

            # دریافت تعداد نهایی
            final_count = ProductPricing.objects.count()

            # دریافت تعداد از سرور برای مقایسه
            server_ids = self.get_server_ids(ProductPricing)
            if server_ids is not None:
                server_count = len(server_ids)

                if final_count == server_count:
                    self.stdout.write(f"\n🎯 ProductPricing: تطابق کامل ✅ (لوکال: {final_count} | سرور: {server_count})")
                else:
                    self.stdout.write(f"\n⚠️ ProductPricing: عدم تطابق ❌ (لوکال: {final_count} | سرور: {server_count})")

                    # اگر هنوز مشکل وجود دارد، پاکسازی کامل و انتقال مجدد
                    if final_count > server_count:
                        self.stdout.write("🔄 اجرای پاکسازی و انتقال مجدد ProductPricing...")
                        ProductPricing.objects.all().delete()
                        retry_count = self.sync_single_model(ProductPricing)
                        self.stdout.write(f"🔄 انتقال مجدد: {retry_count} رکورد")

        except Exception as e:
            self.stdout.write(f"⚠️ خطا در بررسی ویژه ProductPricing: {e}")