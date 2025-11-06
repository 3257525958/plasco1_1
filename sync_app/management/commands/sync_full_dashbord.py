from django.core.management.base import BaseCommand
from django.conf import settings
import requests
from django.apps import apps


class Command(BaseCommand):
    help = 'انتقال کامل تمام داده‌های dashbord_app از سرور به لوکال'

    def handle(self, *args, **options):
        if not settings.OFFLINE_MODE:
            self.stdout.write("❌ فقط در حالت آفلاین قابل اجراست")
            return

        self.stdout.write("🚀 شروع انتقال کامل dashbord_app از سرور به لوکال...")

        # مدل‌های dashbord_app - فقط مدل‌های موجود
        models_to_sync = [
            'Froshande',
            'Product',
            'BankAccount',
            'ContactNumber',
            'Invoice',
            'InvoiceItem',
            # حذف SaleInvoice و SaleItem چون وجود ندارند
        ]

        total_synced = 0

        for model_name in models_to_sync:
            try:
                model_class = apps.get_model('dashbord_app', model_name)
                synced_count = self.sync_model_data(model_class)
                total_synced += synced_count
                self.stdout.write(f"✅ {model_name}: {synced_count} رکورد")
            except Exception as e:
                self.stdout.write(f"❌ خطا در {model_name}: {e}")

        self.stdout.write(
            self.style.SUCCESS(f"🎉 انتقال کامل شد! مجموع: {total_synced} رکورد")
        )

        # نمایش وضعیت نهایی
        self.show_final_status()

    def sync_model_data(self, model_class):
        """دریافت و ذخیره داده‌های یک مدل از سرور"""
        try:
            response = requests.get(
                f"{settings.ONLINE_SERVER_URL}/api/sync/model-data/",
                params={'app': 'dashbord_app', 'model': model_class.__name__},
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    records = data.get('records', [])
                    return self.save_records(model_class, records)
            else:
                self.stdout.write(f"⚠️ خطا در پاسخ سرور برای {model_class.__name__}: {response.status_code}")

            return 0

        except Exception as e:
            self.stdout.write(f"⚠️ خطا در دریافت داده‌های {model_class.__name__}: {e}")
            return 0

    def save_records(self, model_class, records):
        """ذخیره رکوردها در دیتابیس لوکال"""
        saved_count = 0

        for record_data in records:
            try:
                record_id = record_data.get('id')
                if not record_id:
                    continue

                # پردازش داده‌ها
                processed_data = self.process_record_data(record_data, model_class)

                # ایجاد یا آپدیت رکورد
                obj, created = model_class.objects.update_or_create(
                    id=record_id,
                    defaults=processed_data
                )
                saved_count += 1

                # لاگ تغییرات برای مدل‌های مهم
                if model_class.__name__ in ['Invoice']:
                    action = "ایجاد" if created else "آپدیت"
                    if saved_count <= 10:  # فقط 10 تا اول را نمایش بده
                        self.stdout.write(
                            f"📝 تغییر ثبت شد (آفلاین): dashbord_app.{model_class.__name__} - ID: {record_id} - Action: {action}")

            except Exception as e:
                error_msg = str(e)
                if "FOREIGN KEY" in error_msg:
                    # خطای وابستگی خارجی - رکورد را نادیده بگیر
                    pass
                else:
                    if saved_count <= 10:  # فقط 10 خطای اول را نمایش بده
                        self.stdout.write(f"⚠️ خطا در ذخیره رکورد {record_id}: {e}")
                continue

        return saved_count

    def process_record_data(self, record_data, model_class):
        """پردازش و تبدیل داده‌های رکورد قبل از ذخیره"""
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

            # سایر فیلدها
            else:
                processed_data[field_name] = value

        return processed_data

    def is_decimal_field(self, model_class, field_name):
        """بررسی اینکه آیا فیلد از نوع Decimal است"""
        try:
            field = model_class._meta.get_field(field_name)
            return field.get_internal_type() in ['DecimalField', 'FloatField']
        except:
            return False

    def show_final_status(self):
        """نمایش وضعیت نهایی dashbord_app"""
        try:
            from dashbord_app.models import (
                Froshande, Product, BankAccount, ContactNumber,
                Invoice, InvoiceItem
            )

            self.stdout.write(f"\n📋 وضعیت نهایی dashbord_app:")

            model_stats = {
                'Froshande': Froshande.objects.count(),
                'Product': Product.objects.count(),
                'BankAccount': BankAccount.objects.count(),
                'ContactNumber': ContactNumber.objects.count(),
                'Invoice': Invoice.objects.count(),
                'InvoiceItem': InvoiceItem.objects.count(),
            }

            for model_name, count in model_stats.items():
                status = "✅" if count > 0 else "⚠️"
                self.stdout.write(f"   {status} {model_name}: {count} رکورد")

        except Exception as e:
            self.stdout.write(f"⚠️ خطا در بررسی وضعیت نهایی: {e}")