# from django.core.management.base import BaseCommand
# from django.conf import settings
# import requests
# from django.apps import apps
#
#
# class Command(BaseCommand):
#     help = 'انتقال کامل تمام داده‌های account_app از سرور به لوکال'
#
#     def handle(self, *args, **options):
#         if not settings.OFFLINE_MODE:
#             self.stdout.write("❌ فقط در حالت آفلاین قابل اجراست")
#             return
#
#         self.stdout.write("🚀 شروع انتقال کامل account_app از سرور به لوکال...")
#
#         # مدل‌های account_app - به ترتیب وابستگی با اولویت‌بندی جدید
#         models_to_sync = [
#             # اول: مدل‌های مستقل
#             'Product',
#             'ProductPricing',
#             'PaymentMethod',
#
#             # دوم: مدل‌هایی که فقط به مدل‌های داخلی وابسته هستند
#             'Expense',
#             'ExpenseImage',
#             'StockTransaction',
#             'InventoryCount',
#
#             # سوم: مدل‌هایی که به اپ‌های دیگر وابسته هستند (اختیاری)
#             # 'FinancialDocument',      # وابسته به dashbord_app.Invoice
#             # 'FinancialDocumentItem',  # وابسته به FinancialDocument
#         ]
#
#         total_synced = 0
#
#         for model_name in models_to_sync:
#             try:
#                 model_class = apps.get_model('account_app', model_name)
#                 synced_count = self.sync_model_data(model_class)
#                 total_synced += synced_count
#                 self.stdout.write(f"✅ {model_name}: {synced_count} رکورد")
#             except Exception as e:
#                 self.stdout.write(f"❌ خطا در {model_name}: {e}")
#
#         self.stdout.write(
#             self.style.SUCCESS(f"🎉 انتقال کامل شد! مجموع: {total_synced} رکورد")
#         )
#
#         # نمایش وضعیت نهایی
#         self.show_final_status()
#
#     def sync_model_data(self, model_class):
#         """دریافت و ذخیره داده‌های یک مدل از سرور"""
#         try:
#             # درخواست مستقیم از سرور برای داده‌های این مدل
#             response = requests.get(
#                 f"{settings.ONLINE_SERVER_URL}/api/sync/model-data/",
#                 params={'app': 'account_app', 'model': model_class.__name__},
#                 timeout=30
#             )
#
#             if response.status_code == 200:
#                 data = response.json()
#                 if data.get('status') == 'success':
#                     records = data.get('records', [])
#                     return self.save_records(model_class, records)
#             else:
#                 self.stdout.write(f"⚠️ خطا در پاسخ سرور برای {model_class.__name__}: {response.status_code}")
#
#             return 0
#
#         except Exception as e:
#             self.stdout.write(f"⚠️ خطا در دریافت داده‌های {model_class.__name__}: {e}")
#             return 0
#
#     def save_records(self, model_class, records):
#         """ذخیره رکوردها در دیتابیس لوکال"""
#         saved_count = 0
#
#         for record_data in records:
#             try:
#                 # استخراج ID از داده‌ها
#                 record_id = record_data.get('id')
#                 if not record_id:
#                     continue
#
#                 # تبدیل مقادیر Decimal و مدیریت فیلدهای خاص
#                 processed_data = self.process_record_data(record_data, model_class)
#
#                 # ایجاد یا آپدیت رکورد
#                 obj, created = model_class.objects.update_or_create(
#                     id=record_id,
#                     defaults=processed_data
#                 )
#                 saved_count += 1
#
#                 # لاگ تغییرات برای مدل‌های خاص
#                 if model_class.__name__ in ['InventoryCount', 'Expense']:
#                     action = "ایجاد" if created else "آپدیت"
#                     self.stdout.write(
#                         f"📝 تغییر ثبت شد (آفلاین): account_app.{model_class.__name__} - ID: {record_id} - Action: {action}")
#
#             except Exception as e:
#                 error_msg = str(e)
#                 if "FOREIGN KEY" in error_msg:
#                     # خطای وابستگی خارجی - رکورد را نادیده بگیر
#                     self.stdout.write(f"⏭️ رد رکورد {record_id} به دلیل وابستگی خارجی")
#                 else:
#                     self.stdout.write(f"⚠️ خطا در ذخیره رکورد {record_id}: {e}")
#                 continue
#
#         return saved_count
#
#     def process_record_data(self, record_data, model_class):
#         """پردازش و تبدیل داده‌های رکورد قبل از ذخیره"""
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
#             # سایر فیلدها
#             else:
#                 processed_data[field_name] = value
#
#         return processed_data
#
#     def is_decimal_field(self, model_class, field_name):
#         """بررسی اینکه آیا فیلد از نوع Decimal است"""
#         try:
#             field = model_class._meta.get_field(field_name)
#             return field.get_internal_type() in ['DecimalField', 'FloatField']
#         except:
#             return False
#
#     def show_final_status(self):
#         """نمایش وضعیت نهایی account_app"""
#         try:
#             from account_app.models import (
#                 Product, ProductPricing, PaymentMethod, Expense,
#                 ExpenseImage, StockTransaction, InventoryCount
#             )
#
#             self.stdout.write(f"\n📋 وضعیت نهایی account_app:")
#
#             model_stats = {
#                 'Product': Product.objects.count(),
#                 'ProductPricing': ProductPricing.objects.count(),
#                 'PaymentMethod': PaymentMethod.objects.count(),
#                 'Expense': Expense.objects.count(),
#                 'ExpenseImage': ExpenseImage.objects.count(),
#                 'StockTransaction': StockTransaction.objects.count(),
#                 'InventoryCount': InventoryCount.objects.count(),
#             }
#
#             for model_name, count in model_stats.items():
#                 status = "✅" if count > 0 else "⚠️"
#                 self.stdout.write(f"   {status} {model_name}: {count} رکورد")
#
#         except Exception as e:
#             self.stdout.write(f"⚠️ خطا در بررسی وضعیت نهایی: {e}")


from django.core.management.base import BaseCommand
from django.conf import settings
import requests
from django.apps import apps
from django.db import transaction


class Command(BaseCommand):
    help = 'انتقال کامل account_app با مدیریت وابستگی‌ها'

    def handle(self, *args, **options):
        if not settings.OFFLINE_MODE:
            self.stdout.write("❌ فقط در حالت آفلاین قابل اجراست")
            return

        self.stdout.write("🚀 شروع انتقال کامل account_app با مدیریت وابستگی‌ها...")

        # مرحله 1: انتقال مدل‌های مستقل
        self.stdout.write("\n📦 مرحله 1: انتقال مدل‌های مستقل...")
        independent_models = ['Product', 'ProductPricing', 'PaymentMethod']
        self.sync_models(independent_models)

        # مرحله 2: انتقال مدل‌های با وابستگی داخلی
        self.stdout.write("\n📦 مرحله 2: انتقال مدل‌های با وابستگی داخلی...")
        dependent_models = ['Expense', 'ExpenseImage', 'StockTransaction']
        self.sync_models(dependent_models)

        # مرحله 3: انتقال InventoryCount با مدیریت ویژه
        self.stdout.write("\n📦 مرحله 3: انتقال InventoryCount...")
        self.sync_inventory_count()

        self.stdout.write(
            self.style.SUCCESS("\n🎉 انتقال کامل account_app با موفقیت انجام شد!")
        )

    def sync_models(self, model_names):
        """انتقال گروهی از مدل‌ها"""
        for model_name in model_names:
            try:
                model_class = apps.get_model('account_app', model_name)
                count = self.sync_model_with_retry(model_class)
                self.stdout.write(f"✅ {model_name}: {count} رکورد")
            except Exception as e:
                self.stdout.write(f"❌ خطا در {model_name}: {e}")

    def sync_model_with_retry(self, model_class, max_retries=3):
        """انتقال یک مدل با قابلیت تکرار در صورت خطا"""
        for attempt in range(max_retries):
            try:
                return self.sync_single_model(model_class)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                self.stdout.write(f"⚠️ تلاش مجدد {attempt + 1} برای {model_class.__name__}")

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
                return self.save_records_safe(model_class, records)
        return 0

    def save_records_safe(self, model_class, records):
        """ذخیره امن رکوردها با مدیریت خطاهای وابستگی"""
        saved_count = 0

        for record_data in records:
            try:
                record_id = record_data.get('id')
                if not record_id:
                    continue

                # پردازش داده‌ها با مدیریت ویژه برای فیلدهای وابسته
                processed_data = self.process_with_dependency_check(record_data, model_class)

                # ایجاد یا آپدیت
                obj, created = model_class.objects.update_or_create(
                    id=record_id,
                    defaults=processed_data
                )
                saved_count += 1

            except Exception as e:
                error_msg = str(e)
                if "FOREIGN KEY" in error_msg:
                    # خطای وابستگی - ایجاد رکورد با مقادیر پیش‌فرض برای فیلدهای وابسته
                    saved_count += self.handle_foreign_key_error(model_class, record_data, record_id, error_msg)
                else:
                    self.stdout.write(f"⚠️ خطا در ذخیره رکورد {record_id}: {e}")
                continue

        return saved_count

    def process_with_dependency_check(self, record_data, model_class):
        """پردازش داده‌ها با بررسی وابستگی‌ها"""
        processed_data = {}

        for field_name, value in record_data.items():
            if value is None:
                processed_data[field_name] = None
                continue

            # مدیریت فیلدهای ForeignKey
            if field_name.endswith('_id') and isinstance(value, int):
                if self.check_foreign_key_exists(field_name, value):
                    processed_data[field_name] = value
                else:
                    # اگر وابستگی وجود ندارد، از مقدار پیش‌فرض استفاده کن
                    processed_data[field_name] = self.get_default_foreign_key(field_name)

            # مدیریت فیلدهای Decimal
            elif isinstance(value, (int, float)) and self.is_decimal_field(model_class, field_name):
                from decimal import Decimal
                processed_data[field_name] = Decimal(str(value))

            # سایر فیلدها
            else:
                processed_data[field_name] = value

        return processed_data

    def check_foreign_key_exists(self, field_name, value):
        """بررسی وجود رکورد وابسته"""
        try:
            # استخراج نام مدل از فیلد (مثلاً branch_id -> Branch)
            model_name = field_name.replace('_id', '').title()
            model_class = apps.get_model('cantact_app', model_name)
            return model_class.objects.filter(id=value).exists()
        except:
            try:
                # اگر در cantact_app نبود، در auth بررسی کن
                if field_name in ['counter_id', 'user_id']:
                    from django.contrib.auth.models import User
                    return User.objects.filter(id=value).exists()
            except:
                pass
        return False

    def get_default_foreign_key(self, field_name):
        """دریافت مقدار پیش‌فرض برای فیلدهای وابسته"""
        try:
            if field_name == 'branch_id':
                from cantact_app.models import Branch
                default_branch = Branch.objects.first()
                return default_branch.id if default_branch else 1
            elif field_name in ['counter_id', 'user_id']:
                from django.contrib.auth.models import User
                default_user = User.objects.first()
                return default_user.id if default_user else 1
        except:
            pass
        return 1  # مقدار پیش‌فرض

    def sync_inventory_count(self):
        """انتقال ویژه InventoryCount"""
        try:
            model_class = apps.get_model('account_app', 'InventoryCount')

            # دریافت تمام رکوردها
            response = requests.get(
                f"{settings.ONLINE_SERVER_URL}/api/sync/model-data/",
                params={'app': 'account_app', 'model': 'InventoryCount'},
                timeout=60
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    records = data.get('records', [])

                    self.stdout.write(f"📊 تعداد رکوردهای InventoryCount در سرور: {len(records)}")

                    saved_count = 0
                    for record_data in records:
                        try:
                            record_id = record_data.get('id')
                            if not record_id:
                                continue

                            # پردازش ویژه برای InventoryCount
                            processed_data = self.process_inventory_data(record_data)

                            with transaction.atomic():
                                obj, created = model_class.objects.update_or_create(
                                    id=record_id,
                                    defaults=processed_data
                                )
                                saved_count += 1

                                if saved_count % 100 == 0:
                                    self.stdout.write(f"📝 {saved_count} رکورد InventoryCount پردازش شد...")

                        except Exception as e:
                            self.stdout.write(f"⚠️ خطا در InventoryCount {record_id}: {e}")
                            continue

                    self.stdout.write(f"✅ InventoryCount: {saved_count} رکورد")
                    return saved_count

            return 0

        except Exception as e:
            self.stdout.write(f"❌ خطا در انتقال InventoryCount: {e}")
            return 0

    def process_inventory_data(self, record_data):
        """پردازش ویژه داده‌های InventoryCount"""
        processed_data = {}

        # فیلدهای اصلی
        inventory_fields = [
            'product_name', 'is_new', 'quantity', 'count_date',
            'created_at', 'barcode_data', 'selling_price', 'profit_percentage'
        ]

        for field in inventory_fields:
            if field in record_data:
                value = record_data[field]
                if value is not None:
                    if field in ['selling_price', 'profit_percentage']:
                        from decimal import Decimal
                        processed_data[field] = Decimal(str(value))
                    else:
                        processed_data[field] = value

        # مدیریت فیلدهای وابسته
        branch_id = record_data.get('branch_id')
        counter_id = record_data.get('counter_id')

        processed_data['branch_id'] = self.get_default_foreign_key('branch_id') if not self.check_foreign_key_exists(
            'branch_id', branch_id) else branch_id
        processed_data['counter_id'] = self.get_default_foreign_key('counter_id') if not self.check_foreign_key_exists(
            'counter_id', counter_id) else counter_id

        return processed_data

    def is_decimal_field(self, model_class, field_name):
        """بررسی فیلدهای Decimal"""
        try:
            field = model_class._meta.get_field(field_name)
            return field.get_internal_type() in ['DecimalField', 'FloatField']
        except:
            return False

    def handle_foreign_key_error(self, model_class, record_data, record_id, error_msg):
        """مدیریت خطاهای وابستگی"""
        try:
            # برای InventoryCount، با مقادیر پیش‌فرض ذخیره کن
            if model_class.__name__ == 'InventoryCount':
                processed_data = self.process_inventory_data(record_data)
                obj, created = model_class.objects.update_or_create(
                    id=record_id,
                    defaults=processed_data
                )
                return 1
        except Exception as e:
            self.stdout.write(f"⚠️ خطا در مدیریت وابستگی برای {record_id}: {e}")

        return 0