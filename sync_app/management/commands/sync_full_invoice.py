from django.core.management.base import BaseCommand
from django.conf import settings
import requests
from django.apps import apps
from django.db import transaction
from decimal import Decimal
from datetime import datetime


class Command(BaseCommand):
    help = 'انتقال کامل تمام داده‌های invoice_app از سرور به لوکال با مدیریت وابستگی‌ها'

    def handle(self, *args, **options):
        if not settings.OFFLINE_MODE:
            self.stdout.write("❌ فقط در حالت آفلاین قابل اجراست")
            return

        self.stdout.write("🚀 شروع انتقال کامل invoice_app با مدیریت وابستگی‌ها...")

        # مرحله 1: انتقال مدل‌های مستقل در invoice_app
        self.stdout.write("\n📦 مرحله 1: انتقال مدل‌های مستقل...")
        independent_models = ['POSDevice', 'POSTransaction']
        self.sync_models(independent_models)

        # مرحله 2: انتقال Invoicefrosh
        self.stdout.write("\n📦 مرحله 2: انتقال Invoicefrosh...")
        self.sync_invoicefrosh()

        # مرحله 3: انتقال مدل‌های وابسته به Invoicefrosh
        self.stdout.write("\n📦 مرحله 3: انتقال مدل‌های وابسته...")
        dependent_models = ['InvoiceItemfrosh', 'CheckPayment', 'CreditPayment']
        self.sync_models(dependent_models)

        self.stdout.write(
            self.style.SUCCESS("\n🎉 انتقال کامل invoice_app با موفقیت انجام شد!")
        )

        # نمایش وضعیت نهایی
        self.show_final_status()

    def sync_models(self, model_names):
        """انتقال گروهی از مدل‌ها"""
        for model_name in model_names:
            try:
                model_class = apps.get_model('invoice_app', model_name)
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
            params={'app': 'invoice_app', 'model': model_class.__name__},
            timeout=60
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

                if saved_count % 50 == 0:  # هر 50 رکورد گزارش بده
                    self.stdout.write(f"📝 {saved_count} رکورد {model_class.__name__} پردازش شد...")

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

            # مدیریت فیلدهای تاریخ
            elif field_name.endswith('_date') or field_name in ['created_at', 'updated_at', 'invoice_date', 'due_date',
                                                                'check_date', 'payment_date']:
                from django.utils import timezone
                from datetime import datetime
                try:
                    if isinstance(value, str):
                        # تبدیل رشته به تاریخ
                        processed_data[field_name] = datetime.fromisoformat(value.replace('Z', '+00:00'))
                    else:
                        processed_data[field_name] = value
                except:
                    processed_data[field_name] = value

            # مدیریت فیلدهای بولین
            elif isinstance(value, bool):
                processed_data[field_name] = value
            elif isinstance(value, str) and value.lower() in ['true', 'false', '1', '0']:
                processed_data[field_name] = value.lower() in ['true', '1']

            # سایر فیلدها
            else:
                processed_data[field_name] = value

        return processed_data

    def check_foreign_key_exists(self, field_name, value):
        """بررسی وجود رکورد وابسته"""
        try:
            if field_name == 'branch_id':
                from cantact_app.models import Branch
                return Branch.objects.filter(id=value).exists()
            elif field_name in ['created_by_id', 'user_id']:
                from django.contrib.auth.models import User
                return User.objects.filter(id=value).exists()
            elif field_name == 'product_id':
                from account_app.models import InventoryCount
                return InventoryCount.objects.filter(id=value).exists()
            elif field_name == 'froshande_id':
                from dashbord_app.models import Froshande
                return Froshande.objects.filter(id=value).exists()
            elif field_name == 'invoice_id':
                from invoice_app.models import Invoicefrosh
                return Invoicefrosh.objects.filter(id=value).exists()
            elif field_name == 'pos_device_id':
                from invoice_app.models import POSDevice
                return POSDevice.objects.filter(id=value).exists()
        except Exception as e:
            self.stdout.write(f"⚠️ خطا در بررسی وابستگی {field_name}: {e}")

        return False

    def get_default_foreign_key(self, field_name):
        """دریافت مقدار پیش‌فرض برای فیلدهای وابسته"""
        try:
            if field_name == 'branch_id':
                from cantact_app.models import Branch
                default_branch = Branch.objects.first()
                return default_branch.id if default_branch else 1
            elif field_name in ['created_by_id', 'user_id']:
                from django.contrib.auth.models import User
                default_user = User.objects.first()
                return default_user.id if default_user else 1
            elif field_name == 'product_id':
                from account_app.models import InventoryCount
                default_product = InventoryCount.objects.first()
                return default_product.id if default_product else 1
            elif field_name == 'froshande_id':
                from dashbord_app.models import Froshande
                default_froshande = Froshande.objects.first()
                return default_froshande.id if default_froshande else 1
            elif field_name == 'invoice_id':
                from invoice_app.models import Invoicefrosh
                default_invoice = Invoicefrosh.objects.first()
                return default_invoice.id if default_invoice else 1
            elif field_name == 'pos_device_id':
                from invoice_app.models import POSDevice
                default_pos = POSDevice.objects.first()
                return default_pos.id if default_pos else 1
        except Exception as e:
            self.stdout.write(f"⚠️ خطا در دریافت پیش‌فرض برای {field_name}: {e}")

        return 1  # مقدار پیش‌فرض

    def sync_invoicefrosh(self):
        """انتقال ویژه Invoicefrosh"""
        try:
            model_class = apps.get_model('invoice_app', 'Invoicefrosh')

            # دریافت تمام رکوردها
            response = requests.get(
                f"{settings.ONLINE_SERVER_URL}/api/sync/model-data/",
                params={'app': 'invoice_app', 'model': 'Invoicefrosh'},
                timeout=60
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    records = data.get('records', [])

                    self.stdout.write(f"📊 تعداد رکوردهای Invoicefrosh در سرور: {len(records)}")

                    saved_count = 0
                    for record_data in records:
                        try:
                            record_id = record_data.get('id')
                            if not record_id:
                                continue

                            # پردازش ویژه برای Invoicefrosh
                            processed_data = self.process_invoicefrosh_data(record_data)

                            with transaction.atomic():
                                obj, created = model_class.objects.update_or_create(
                                    id=record_id,
                                    defaults=processed_data
                                )
                                saved_count += 1

                                if saved_count % 50 == 0:
                                    self.stdout.write(f"📝 {saved_count} رکورد Invoicefrosh پردازش شد...")

                        except Exception as e:
                            self.stdout.write(f"⚠️ خطا در Invoicefrosh {record_id}: {e}")
                            continue

                    self.stdout.write(f"✅ Invoicefrosh: {saved_count} رکورد")
                    return saved_count

            return 0

        except Exception as e:
            self.stdout.write(f"❌ خطا در انتقال Invoicefrosh: {e}")
            return 0

    def process_invoicefrosh_data(self, record_data):
        """پردازش ویژه داده‌های Invoicefrosh"""
        processed_data = {}

        # فیلدهای اصلی Invoicefrosh
        invoice_fields = [
            'payment_date', 'payment_method', 'total_amount', 'total_without_discount',
            'discount', 'is_finalized', 'is_paid', 'customer_name', 'customer_phone',
            'serial_number', 'paid_amount', 'created_at'
        ]

        for field in invoice_fields:
            if field in record_data:
                value = record_data[field]
                if value is not None:
                    if field in ['total_amount', 'total_without_discount', 'discount', 'paid_amount']:
                        processed_data[field] = int(value) if value else 0
                    elif field in ['payment_date', 'created_at']:
                        from django.utils import timezone
                        from datetime import datetime
                        try:
                            if isinstance(value, str):
                                processed_data[field] = datetime.fromisoformat(value.replace('Z', '+00:00'))
                            else:
                                processed_data[field] = value
                        except:
                            processed_data[field] = value
                    elif field in ['is_finalized', 'is_paid']:
                        if isinstance(value, str):
                            processed_data[field] = value.lower() in ['true', '1', 'yes']
                        else:
                            processed_data[field] = bool(value)
                    else:
                        processed_data[field] = value

        # مدیریت فیلدهای وابسته
        branch_id = record_data.get('branch_id')
        created_by_id = record_data.get('created_by_id')
        pos_device_id = record_data.get('pos_device_id')

        processed_data['branch_id'] = self.get_default_foreign_key('branch_id') if not self.check_foreign_key_exists(
            'branch_id', branch_id) else branch_id
        processed_data['created_by_id'] = self.get_default_foreign_key(
            'created_by_id') if not self.check_foreign_key_exists('created_by_id', created_by_id) else created_by_id
        processed_data['pos_device_id'] = self.get_default_foreign_key(
            'pos_device_id') if not self.check_foreign_key_exists('pos_device_id', pos_device_id) else pos_device_id

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
            # برای Invoicefrosh، با مقادیر پیش‌فرض ذخیره کن
            if model_class.__name__ == 'Invoicefrosh':
                processed_data = self.process_invoicefrosh_data(record_data)
                obj, created = model_class.objects.update_or_create(
                    id=record_id,
                    defaults=processed_data
                )
                return 1

            # برای InvoiceItemfrosh، با مقادیر پیش‌فرض ذخیره کن
            elif model_class.__name__ == 'InvoiceItemfrosh':
                processed_data = self.process_invoice_item_data(record_data)
                obj, created = model_class.objects.update_or_create(
                    id=record_id,
                    defaults=processed_data
                )
                return 1

            # برای سایر مدل‌ها
            else:
                processed_data = self.process_with_dependency_check(record_data, model_class)
                obj, created = model_class.objects.update_or_create(
                    id=record_id,
                    defaults=processed_data
                )
                return 1

        except Exception as e:
            self.stdout.write(f"⚠️ خطا در مدیریت وابستگی برای {record_id}: {e}")

        return 0

    def process_invoice_item_data(self, record_data):
        """پردازش ویژه داده‌های InvoiceItemfrosh"""
        processed_data = {}

        # فیلدهای اصلی InvoiceItemfrosh
        item_fields = [
            'quantity', 'price', 'total_price', 'standard_price', 'discount'
        ]

        for field in item_fields:
            if field in record_data:
                value = record_data[field]
                if value is not None:
                    processed_data[field] = int(value) if value else 0

        # مدیریت فیلدهای وابسته
        invoice_id = record_data.get('invoice_id')
        product_id = record_data.get('product_id')

        processed_data['invoice_id'] = self.get_default_foreign_key('invoice_id') if not self.check_foreign_key_exists(
            'invoice_id', invoice_id) else invoice_id
        processed_data['product_id'] = self.get_default_foreign_key('product_id') if not self.check_foreign_key_exists(
            'product_id', product_id) else product_id

        return processed_data

    def show_final_status(self):
        """نمایش وضعیت نهایی invoice_app"""
        try:
            from invoice_app.models import POSDevice, Invoicefrosh, InvoiceItemfrosh, CheckPayment, CreditPayment, \
                POSTransaction

            self.stdout.write(f"\n📋 وضعیت نهایی invoice_app:")

            model_stats = {
                'POSDevice': POSDevice.objects.count(),
                'Invoicefrosh': Invoicefrosh.objects.count(),
                'InvoiceItemfrosh': InvoiceItemfrosh.objects.count(),
                'CheckPayment': CheckPayment.objects.count(),
                'CreditPayment': CreditPayment.objects.count(),
                'POSTransaction': POSTransaction.objects.count(),
            }

            for model_name, count in model_stats.items():
                status = "✅" if count > 0 else "⚠️"
                self.stdout.write(f"   {status} {model_name}: {count} رکورد")

        except Exception as e:
            self.stdout.write(f"⚠️ خطا در بررسی وضعیت نهایی: {e}")