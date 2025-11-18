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

                # 🔄 مدیریت ویژه برای InventoryCount - انتقال بدون وابستگی
                if model_class.__name__ == 'InventoryCount':
                    processed_data = self.extract_inventory_essential_data(processed_data)

                # ایجاد یا آپدیت
                obj, created = model_class.objects.update_or_create(
                    id=record_id,
                    defaults=processed_data
                )
                saved_count += 1

            except Exception as e:
                error_count += 1
                # 🔄 راه حل قطعی: انتقال داده‌های اصلی بدون وابستگی
                if model_class.__name__ == 'InventoryCount' and "FOREIGN KEY" in str(e):
                    try:
                        self.stdout.write(f"🔄 اجرای راه حل جایگزین برای InventoryCount ID {record_id}...")

                        # استخراج فقط داده‌های ضروری بدون وابستگی
                        essential_data = self.get_inventory_essential_data(record_data)

                        # ایجاد رکورد جدید با داده‌های اصلی
                        obj, created = model_class.objects.update_or_create(
                            id=record_id,
                            defaults=essential_data
                        )
                        saved_count += 1
                        error_count -= 1
                        self.stdout.write(f"✅ InventoryCount ID {record_id}: انتقال موفق با راه حل جایگزین")
                    except Exception as final_error:
                        self.stdout.write(f"❌ InventoryCount ID {record_id}: انتقال ناموفق - {final_error}")
                else:
                    self.stdout.write(f"⚠️ خطا در {model_class.__name__} ID {record_id}: {str(e)}")
                continue

        if error_count > 0:
            self.stdout.write(f"   ❌ {error_count} خطا در ذخیره")

        return saved_count

    def extract_inventory_essential_data(self, record_data):
        """استخراج داده‌های ضروری InventoryCount بدون وابستگی‌های مشکل‌ساز"""
        essential_fields = [
            'product_name', 'is_new', 'quantity', 'count_date',
            'created_at', 'barcode_data', 'selling_price', 'profit_percentage'
        ]

        processed_data = {}

        for field in essential_fields:
            if field in record_data:
                processed_data[field] = record_data[field]

        # 🔄 استفاده از مقادیر پیش‌فرض برای وابستگی‌ها
        processed_data['branch_id'] = self.get_any_existing_branch_id()
        processed_data['counter_id'] = self.get_any_existing_user_id()

        return processed_data

    def get_inventory_essential_data(self, record_data):
        """دریافت داده‌های اصلی برای InventoryCount (راه حل قطعی)"""
        from decimal import Decimal

        essential_data = {
            'product_name': record_data.get('product_name', ''),
            'is_new': record_data.get('is_new', True),
            'quantity': record_data.get('quantity', 0),
            'count_date': record_data.get('count_date', ''),
            'barcode_data': record_data.get('barcode_data', ''),
            'selling_price': record_data.get('selling_price'),
            'profit_percentage': Decimal(str(record_data.get('profit_percentage', '30.00'))),
            'branch_id': self.get_any_existing_branch_id(),
            'counter_id': self.get_any_existing_user_id()
        }

        # حذف فیلدهای None
        essential_data = {k: v for k, v in essential_data.items() if v is not None}

        return essential_data

    def get_any_existing_branch_id(self):
        """دریافت اولین branch_id موجود"""
        try:
            from cantact_app.models import Branch
            branch = Branch.objects.first()
            return branch.id if branch else 1
        except:
            return 1

    def get_any_existing_user_id(self):
        """دریافت اولین user_id موجود"""
        try:
            from django.contrib.auth.models import User
            user = User.objects.first()
            return user.id if user else 1
        except:
            return 1


    def fix_inventory_dependencies(self, record_data):
        """رفع مشکلات وابستگی‌های InventoryCount"""
        fixed_data = record_data.copy()

        # بررسی و اصلاح branch_id
        branch_id = fixed_data.get('branch_id')
        if branch_id and not self.check_branch_exists(branch_id):
            default_branch = self.get_default_branch()
            fixed_data['branch_id'] = default_branch
            self.stdout.write(f"   🔄 branch_id {branch_id} -> {default_branch}")

        # بررسی و اصلاح counter_id
        counter_id = fixed_data.get('counter_id')
        if counter_id and not self.check_user_exists(counter_id):
            default_user = self.get_default_user()
            fixed_data['counter_id'] = default_user
            self.stdout.write(f"   🔄 counter_id {counter_id} -> {default_user}")

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
            from django.contrib.auth.models import User
            return User.objects.filter(id=user_id).exists()
        except:
            return False

    def get_default_branch(self):
        """دریافت شعبه پیش‌فرض"""
        try:
            from cantact_app.models import Branch
            default_branch = Branch.objects.first()
            return default_branch.id if default_branch else 1
        except:
            return 1

    def get_default_user(self):
        """دریافت کاربر پیش‌فرض"""
        try:
            from django.contrib.auth.models import User
            default_user = User.objects.first()
            return default_user.id if default_user else 1
        except:
            return 1




    def handle(self, *args, **options):
        if not settings.OFFLINE_MODE:
            self.stdout.write("❌ فقط در حالت آفلاین قابل اجراست")
            return

        self.stdout.write("🚀 شروع انتقال کامل account_app...")

        # مرحله 0: بررسی اولیه
        self.stdout.write("\n🔍 مرحله 0: بررسی اولیه داده‌ها...")
        initial_status = self.get_initial_status()

        # 🔄 تغییر ترتیب: ابتدا مدل‌های مستقل، سپس InventoryCount
        self.stdout.write("\n📦 مرحله 1: انتقال مدل‌های مستقل...")
        independent_models = [
            'Product', 'ProductPricing', 'PaymentMethod',
            'Expense', 'ExpenseImage', 'StockTransaction'
        ]

        # 🔄 تغییر: ابتدا مدل‌های مستقل منتقل شوند
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

        # 🔄 تغییر: InventoryCount بعد از همه منتقل شود
        self.stdout.write("\n📦 مرحله 2: انتقال InventoryCount (بعد از وابستگی‌ها)...")
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