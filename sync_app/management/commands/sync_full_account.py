from django.core.management.base import BaseCommand
from django.conf import settings
import requests
from django.apps import apps
from django.db import transaction
from django.db.models import Q
from decimal import Decimal
import math
import time


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

        # مرحله 1: بررسی و ایجاد مدل‌های وابسته اول
        self.stdout.write("\n🔗 مرحله 1: بررسی مدل‌های وابسته...")
        self.check_and_create_dependencies()

        # مرحله 2: انتقال تمام مدل‌های account_app
        self.stdout.write("\n📦 مرحله 2: انتقال تمام مدل‌های account_app...")
        all_models = [
            'Product', 'ProductPricing', 'PaymentMethod',
            'Expense', 'ExpenseImage', 'StockTransaction', 'InventoryCount'
        ]

        transfer_results = {}
        for model_name in all_models:
            try:
                model_class = apps.get_model('account_app', model_name)
                if model_name == 'InventoryCount':
                    transferred_count = self.sync_inventory_count_safe(model_class)
                else:
                    transferred_count = self.sync_single_model(model_class)

                transfer_results[model_name] = transferred_count
                self.stdout.write(f"✅ {model_name}: {transferred_count} رکورد انتقال یافت")
                time.sleep(1)  # استراحت بین مدل‌ها
            except Exception as e:
                self.stdout.write(f"❌ خطا در انتقال {model_name}: {e}")
                transfer_results[model_name] = 0

        # مرحله 3: مقایسه و پاکسازی خودکار
        self.stdout.write("\n🔍 مرحله 3: مقایسه و پاکسازی خودکار...")
        cleanup_results = self.auto_cleanup_all_models()

        # مرحله 4: بررسی نهایی و گزارش
        self.stdout.write("\n📊 مرحله 4: گزارش نهایی...")
        self.generate_final_report(initial_status, transfer_results, cleanup_results)

        self.stdout.write(
            self.style.SUCCESS("\n🎉 انتقال کامل account_app با موفقیت انجام شد!")
        )

    def check_and_create_dependencies(self):
        """بررسی و ایجاد مدل‌های وابسته اولیه"""
        try:
            from cantact_app.models import Branch
            from django.contrib.auth.models import User
            from account_app.models import Product

            # بررسی و ایجاد شعبه پیش‌فرض اگر وجود ندارد
            if not Branch.objects.exists():
                self.stdout.write("📝 ایجاد شعبه پیش‌فرض...")
                default_branch = Branch.objects.create(
                    name='شعبه مرکزی',
                    code='001',
                    address='آدرس پیش‌فرض',
                    phone='02100000000',
                    is_active=True
                )
                self.stdout.write(f"✅ شعبه پیش‌فرض ایجاد شد: {default_branch.name}")
            else:
                self.stdout.write(f"✅ شعبه‌ها موجود هستند: {Branch.objects.count()} شعبه")

            # بررسی و ایجاد کاربر پیش‌فرض اگر وجود ندارد
            if not User.objects.filter(username='admin').exists():
                self.stdout.write("📝 ایجاد کاربر پیش‌فرض...")
                admin_user = User.objects.create_user(
                    username='admin',
                    password='admin123',
                    email='admin@plasco.com',
                    first_name='مدیر',
                    last_name='سیستم',
                    is_active=True,
                    is_staff=True,
                    is_superuser=True
                )
                self.stdout.write(f"✅ کاربر پیش‌فرض ایجاد شد: {admin_user.username}")
            else:
                self.stdout.write(f"✅ کاربران موجود هستند: {User.objects.count()} کاربر")

            # بررسی و ایجاد محصول پیش‌فرض اگر نیاز باشد
            if not Product.objects.exists():
                self.stdout.write("📝 ایجاد محصول پیش‌فرض...")
                default_product = Product.objects.create(
                    name='محصول پیش‌فرض',
                    code='000001',
                    description='محصول پیش‌فرض برای سیستم',
                    is_active=True
                )
                self.stdout.write(f"✅ محصول پیش‌فرض ایجاد شد: {default_product.name}")

        except Exception as e:
            self.stdout.write(f"⚠️ خطا در بررسی وابستگی‌ها: {e}")

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
        model_name = model_class.__name__
        self.stdout.write(f"📡 دریافت داده‌های {model_name} از سرور...")

        try:
            response = requests.get(
                f"{settings.ONLINE_SERVER_URL}/api/sync/model-data/",
                params={'app': 'account_app', 'model': model_name},
                timeout=60
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    records = data.get('records', [])
                    self.stdout.write(f"📥 دریافت {len(records)} رکورد برای {model_name}")
                    if records:
                        return self.save_records_safe(model_class, records)
                    else:
                        self.stdout.write(f"⚠️ هیچ رکوردی برای {model_name} دریافت نشد")
                        return 0
                else:
                    self.stdout.write(f"⚠️ وضعیت ناموفق از سرور برای {model_name}")
                    return 0
            else:
                self.stdout.write(f"⚠️ خطا در پاسخ سرور برای {model_name}: {response.status_code}")
                return 0

        except requests.exceptions.Timeout:
            self.stdout.write(f"❌ timeout در دریافت داده‌های {model_name}")
            return 0
        except Exception as e:
            self.stdout.write(f"❌ خطا در دریافت {model_name}: {e}")
            return 0

    def save_records_safe(self, model_class, records):
        """ذخیره امن رکوردها"""
        saved_count = 0
        error_count = 0
        model_name = model_class.__name__

        for index, record_data in enumerate(records, 1):
            try:
                record_id = record_data.get('id')
                if not record_id:
                    self.stdout.write(f"⚠️ رکورد بدون ID در {model_name} نادیده گرفته شد")
                    continue

                # حذف فیلدهای ForeignKey که ممکن است مشکل ایجاد کنند
                safe_data = {}
                for key, value in record_data.items():
                    # اگر فیلد با _id تمام می‌شود (مثل branch_id)، آن را نادیده بگیریم
                    if key.endswith('_id') and key not in ['id']:
                        # فقط برای InventoryCount به طور خاص مدیریت می‌کنیم
                        if model_name != 'InventoryCount':
                            continue

                    # برای سایر فیلدها
                    safe_data[key] = value

                # ایجاد یا آپدیت
                obj, created = model_class.objects.update_or_create(
                    id=record_id,
                    defaults=safe_data
                )
                saved_count += 1

                # نمایش پیشرفت برای تعداد زیاد
                if len(records) > 50 and index % 50 == 0:
                    self.stdout.write(f"📝 {index}/{len(records)} رکورد {model_name} پردازش شد...")

            except Exception as e:
                error_count += 1
                # فقط 5 خطای اول را نمایش بده
                if error_count <= 5:
                    self.stdout.write(f"❌ خطا در رکورد {record_id} از {model_name}: {str(e)[:100]}")
                continue

        if error_count > 0:
            self.stdout.write(f"⚠️ مجموع خطاها در {model_name}: {error_count}")

        return saved_count

    def sync_inventory_count_safe(self, model_class):
        """همگام‌سازی امن مدل InventoryCount با مدیریت فیلدهای وابسته"""
        self.stdout.write("📡 دریافت داده‌های InventoryCount از سرور...")

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
                    self.stdout.write(f"📥 دریافت {len(records)} رکورد InventoryCount")
                    if records:
                        return self.save_inventory_count_records(model_class, records)
                    else:
                        self.stdout.write("⚠️ هیچ رکورد InventoryCount دریافت نشد")
                        return 0
                else:
                    self.stdout.write("⚠️ وضعیت ناموفق از سرور برای InventoryCount")
                    return 0
            else:
                self.stdout.write(f"⚠️ خطا در پاسخ سرور برای InventoryCount: {response.status_code}")
                return 0

        except requests.exceptions.Timeout:
            self.stdout.write("❌ timeout در دریافت داده‌های InventoryCount")
            return 0
        except Exception as e:
            self.stdout.write(f"❌ خطا در دریافت InventoryCount: {e}")
            return 0

    def save_inventory_count_records(self, model_class, records):
        """ذخیره امن رکوردهای InventoryCount"""
        saved_count = 0
        error_count = 0

        from cantact_app.models import Branch
        from django.contrib.auth.models import User

        # دریافت یا ایجاد شعبه پیش‌فرض
        default_branch = Branch.objects.first()
        if not default_branch:
            default_branch = Branch.objects.create(
                name='شعبه مرکزی',
                code='001',
                address='آدرس پیش‌فرض',
                phone='02100000000',
                is_active=True
            )
            self.stdout.write(f"✅ شعبه پیش‌فرض ایجاد شد: {default_branch.name}")

        # دریافت یا ایجاد کاربر پیش‌فرض
        default_user = User.objects.filter(username='admin').first()
        if not default_user:
            default_user = User.objects.create_user(
                username='admin',
                password='admin123',
                email='admin@plasco.com',
                first_name='مدیر',
                last_name='سیستم',
                is_active=True,
                is_staff=True,
                is_superuser=True
            )
            self.stdout.write(f"✅ کاربر پیش‌فرض ایجاد شد: {default_user.username}")

        for index, record_data in enumerate(records, 1):
            try:
                record_id = record_data.get('id')
                if not record_id:
                    self.stdout.write("⚠️ رکورد InventoryCount بدون ID نادیده گرفته شد")
                    continue

                # پردازش فیلد branch
                branch_id = record_data.get('branch_id')
                if branch_id:
                    try:
                        branch = Branch.objects.get(id=branch_id)
                    except Branch.DoesNotExist:
                        branch = default_branch
                        self.stdout.write(f"⚠️ branch_id={branch_id} وجود ندارد، از شعبه پیش‌فرض استفاده شد")
                else:
                    branch = default_branch

                # پردازش فیلد counter (user)
                counter_id = record_data.get('counter_id')
                if counter_id:
                    try:
                        counter = User.objects.get(id=counter_id)
                    except User.DoesNotExist:
                        counter = default_user
                        self.stdout.write(f"⚠️ counter_id={counter_id} وجود ندارد، از کاربر پیش‌فرض استفاده شد")
                else:
                    counter = default_user

                # آماده‌سازی داده‌ها برای ذخیره
                processed_data = {
                    'product_name': record_data.get('product_name', 'محصول ناشناخته'),
                    'is_new': record_data.get('is_new', True),
                    'quantity': record_data.get('quantity', 0),
                    'count_date': record_data.get('count_date', ''),
                    'barcode_data': record_data.get('barcode_data', ''),
                    'selling_price': record_data.get('selling_price', 0),
                    'branch': branch,
                    'counter': counter,
                    'profit_percentage': Decimal(str(record_data.get('profit_percentage', 70.00)))
                }

                # حذف فیلدهای اضافی که ممکن است با update_or_create تداخل داشته باشند
                if 'branch_id' in processed_data:
                    del processed_data['branch_id']
                if 'counter_id' in processed_data:
                    del processed_data['counter_id']

                # ایجاد یا آپدیت
                obj, created = model_class.objects.update_or_create(
                    id=record_id,
                    defaults=processed_data
                )

                saved_count += 1

                # نمایش پیشرفت
                if len(records) > 50 and index % 50 == 0:
                    self.stdout.write(f"📝 {index}/{len(records)} رکورد InventoryCount پردازش شد...")

            except Exception as e:
                error_count += 1
                if error_count <= 5:
                    self.stdout.write(f"❌ خطا در رکورد {record_id} از InventoryCount: {str(e)[:100]}")
                continue

        if error_count > 0:
            self.stdout.write(f"⚠️ مجموع خطاها در InventoryCount: {error_count}")

        return saved_count

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
        total_final = 0

        for model_name in models_to_report:
            initial = initial_status.get(model_name, 0)
            transferred = transfer_results.get(model_name, 0)
            cleaned = cleanup_results.get(model_name, 0)

            # محاسبه تعداد نهایی
            final_count = initial + transferred - cleaned
            total_final += final_count

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
        self.stdout.write(f"📊 جمع کل نهایی: {total_final} رکورد")
        self.stdout.write("=" * 50)

        # بررسی ویژه InventoryCount
        self.check_inventory_count_special()

    def check_inventory_count_special(self):
        """بررسی ویژه برای InventoryCount"""
        try:
            from account_app.models import InventoryCount

            # دریافت تعداد نهایی
            final_count = InventoryCount.objects.count()

            # بررسی branchها
            from cantact_app.models import Branch
            branch_count = Branch.objects.count()

            # بررسی کاربران
            from django.contrib.auth.models import User
            user_count = User.objects.count()

            self.stdout.write("\n🔍 بررسی ویژه InventoryCount:")
            self.stdout.write(f"   📊 تعداد رکوردها: {final_count}")
            self.stdout.write(f"   🏢 تعداد شعبه‌ها: {branch_count}")
            self.stdout.write(f"   👤 تعداد کاربران: {user_count}")

            # بررسی چند رکورد نمونه
            sample_records = InventoryCount.objects.all()[:3]
            if sample_records:
                self.stdout.write("\n📝 نمونه رکوردهای InventoryCount:")
                for record in sample_records:
                    self.stdout.write(f"   - {record.product_name}: {record.quantity} عدد")

        except Exception as e:
            self.stdout.write(f"⚠️ خطا در بررسی ویژه InventoryCount: {e}")
