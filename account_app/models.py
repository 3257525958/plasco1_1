

from django.contrib.auth import get_user_model
from cantact_app.models import Branch

User = get_user_model()
from decimal import Decimal, InvalidOperation
import hashlib
import jdatetime
from django.db import models, connection
from decimal import Decimal
import random

import math  # این خط را اضافه کنید
from decimal import Decimal, InvalidOperation
import hashlib
import jdatetime
from django.db import models, connection
from decimal import Decimal
import random

class InventoryCount(models.Model):
    product_name = models.CharField(max_length=100, verbose_name="نام کالا")
    is_new = models.BooleanField(default=True, verbose_name="کالای جدید")
    quantity = models.IntegerField(verbose_name="تعداد")
    count_date = models.CharField(max_length=10, verbose_name="تاریخ شمارش", default="")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    barcode_data = models.CharField(max_length=100, blank=True, null=True, verbose_name="داده بارکد")
    selling_price = models.PositiveIntegerField(verbose_name="قیمت فروش", blank=True, null=True)
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, verbose_name="شعبه")
    counter = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name="شمارنده")
    profit_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name="درصد سود",
        default=Decimal('30.00'),
    )

    class Meta:
        verbose_name = "شمارش انبار"
        verbose_name_plural = "شمارش های انبار"
        ordering = ['-created_at']

    def clean(self):
        """
        اعتبارسنجی خودکار قبل از ذخیره‌سازی
        """
        try:
            profit_value = Decimal(str(self.profit_percentage))
            if profit_value < Decimal('0.00') or profit_value > Decimal('10000.00'):
                self.profit_percentage = Decimal('70.00')
        except (TypeError, ValueError, InvalidOperation):
            self.profit_percentage = Decimal('70.00')

    def generate_unique_numeric_barcode(self):
        """تولید بارکد ثابت ۱۲ رقمی بر اساس نام کالا"""
        import hashlib

        # استفاده از نام کالا برای تولید بارکد ثابت
        product_name = self.product_name.strip()

        # تولید کد دیجیتال از نام کالا
        hash_object = hashlib.md5(product_name.encode('utf-8'))
        hash_hex = hash_object.hexdigest()

        # تبدیل به عدد ۱۲ رقمی
        hash_int = int(hash_hex[:8], 16)  # استفاده از ۸ کاراکتر اول
        barcode = str(hash_int % 10 ** 12).zfill(12)

        return barcode


    def save(self, *args, **kwargs):
        self.clean()

        if not self.count_date:
            jalali_date = jdatetime.datetime.now().strftime('%Y/%m/%d')
            self.count_date = jalali_date

        if not self.barcode_data:
            self.barcode_data = self.generate_unique_numeric_barcode()

        print(f"✅ شروع محاسبه قیمت برای کالا: {self.product_name}")

        # ایجاد ProductPricing اگر وجود ندارد
        try:
            from .models import ProductPricing
            pricing = ProductPricing.objects.get(product_name=self.product_name)
            print(f"✅ ProductPricing یافت شد: {pricing}")

        except ProductPricing.DoesNotExist:
            # ایجاد ProductPricing با مقادیر پیشفرض
            pricing = ProductPricing.objects.create(
                product_name=self.product_name,
                highest_purchase_price=Decimal('0'),
                adjustment_percentage=Decimal('0'),
                standard_price=Decimal('0')
            )
            print(f"✅ ProductPricing جدید ایجاد شد برای: {self.product_name}")
        except Exception as e:
            print(f"⚠️ خطا در دسترسی به ProductPricing: {e}")
            pricing = None

        # محاسبه قیمت فروش - نسخه اصلاح شده
        if pricing and pricing.standard_price is not None and pricing.standard_price > 0:
            try:
                # تبدیل profit_percentage به Decimal به طور ایمن
                if isinstance(self.profit_percentage, (int, float)):
                    profit_percentage = Decimal(str(self.profit_percentage))
                elif isinstance(self.profit_percentage, Decimal):
                    profit_percentage = self.profit_percentage
                else:
                    profit_percentage = Decimal('100.00')

                print(f"✅ درصد سود استفاده شده: {profit_percentage}")

                # محاسبه ایمن
                standard_price_decimal = Decimal(str(pricing.standard_price))
                multiplier = Decimal('1') + (profit_percentage / Decimal('100'))
                new_price = standard_price_decimal * multiplier

                # گرد کردن به نزدیکترین 1000
                self.selling_price = int(math.ceil(float(new_price) / 1000) * 1000)
                print(f"✅ قیمت فروش محاسبه و تنظیم شد: {self.selling_price}")

            except Exception as e:
                print(f"⚠️ خطا در محاسبه قیمت: {e}")
                # مقدار پیش‌فرض برای قیمت فروش
                self.selling_price = pricing.standard_price
        else:
            print("⚠️ قیمت معیار صفر یا None است، قیمت فروش تنظیم نشد")
            # اگر pricing وجود ندارد، selling_price رو از داده اصلی نگه دار
            if not hasattr(self, 'selling_price') or self.selling_price is None:
                self.selling_price = 0

        super().save(*args, **kwargs)
        print("✅ متد save با موفقیت اجرا شد.")
    # def save(self, *args, **kwargs):
    #     self.clean()
    #
    #     if not self.count_date:
    #         jalali_date = jdatetime.datetime.now().strftime('%Y/%m/%d')
    #         self.count_date = jalali_date
    #
    #     if not self.barcode_data:
    #         self.barcode_data = self.generate_unique_numeric_barcode()
    #
    #     print(f"✅ شروع محاسبه قیمت برای کالا: {self.product_name}")
    #
    #     # ایجاد ProductPricing اگر وجود ندارد
    #     try:
    #         # import داخلی برای جلوگیری از circular import
    #         from .models import ProductPricing
    #         pricing = ProductPricing.objects.get(product_name=self.product_name)
    #         print(f"✅ ProductPricing یافت شد: {pricing}")
    #     except ProductPricing.DoesNotExist:
    #         # ایجاد ProductPricing با مقادیر پیشفرض
    #         pricing = ProductPricing.objects.create(
    #             product_name=self.product_name,
    #             highest_purchase_price=Decimal('0'),
    #             adjustment_percentage=Decimal('0'),
    #             standard_price=Decimal('0')
    #         )
    #         print(f"✅ ProductPricing جدید ایجاد شد برای: {self.product_name}")
    #     except Exception as e:
    #         print(f"⚠️ خطا در دسترسی به ProductPricing: {e}")
    #         pricing = None
    #
    #     # محاسبه قیمت فروش
    #     if pricing and pricing.standard_price is not None and pricing.standard_price > 0:
    #         try:
    #             profit_percentage = Decimal(str(self.profit_percentage))
    #         except (TypeError, ValueError):
    #             profit_percentage = Decimal('100.00')
    #
    #         print(f"✅ درصد سود استفاده شده: {profit_percentage}")
    #
    #         new_price = pricing.standard_price * (1 + profit_percentage / 100)
    #         self.selling_price = Decimal(math.ceil(new_price / 1000) * 1000)
    #         print(f"✅ قیمت فروش محاسبه و تنظیم شد: {self.selling_price}")
    #     else:
    #         print("⚠️ قیمت معیار صفر یا None است، قیمت فروش تنظیم نشد")
    #
    #     super().save(*args, **kwargs)
    #     print("✅ متد save با موفقیت اجرا شد.")

    def __str__(self):
        try:
            branch_name = self.branch.name if self.branch else "بدون شعبه"
            return f"{self.product_name} - {branch_name} - {self.quantity}"
        except Exception:
            return f"{self.product_name} - {self.quantity}"



from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
class Product(models.Model):
    name = models.CharField(max_length=100, verbose_name="نام محصول", unique=True)
    description = models.TextField(verbose_name="توضیحات", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="آخرین بروزرسانی")

    class Meta:
        verbose_name = "محصول"
        verbose_name_plural = "محصولات"
        ordering = ['name']

    def __str__(self):
        return self.name


class FinancialDocument(models.Model):
    STATUS_CHOICES = [
        ('unpaid', 'پرداخت نشده'),
        ('partially_paid', 'تا اندازه ای پرداخت شده'),
        ('settled', 'تسویه حساب'),
    ]

    invoice = models.OneToOneField(
        'dashbord_app.Invoice',
        on_delete=models.CASCADE,
        related_name='financial_document'
    )
    document_date = models.DateTimeField(auto_now_add=True)
    total_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name="مبلغ کل"
    )
    paid_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))],
        default=Decimal('0'),
        verbose_name="مبلغ پرداخت شده"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='unpaid',
        verbose_name="وضعیت پرداخت"
    )

    def __str__(self):
        return f"سند مالی {self.invoice.serial_number}"

    class Meta:
        verbose_name = "سند مالی"
        verbose_name_plural = "اسناد مالی"


class FinancialDocumentItem(models.Model):
    document = models.ForeignKey(
        FinancialDocument,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product_name = models.CharField(max_length=200, verbose_name="نام کالا")
    quantity = models.IntegerField(verbose_name="تعداد")
    unit_price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name="قیمت واحد"
    )
    discount = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0'),
        verbose_name="تخفیف (%)"
    )
    total_price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name="قیمت کل"
    )

    def __str__(self):
        return f"{self.product_name} - {self.quantity}x"

    class Meta:
        verbose_name = "آیتم سند مالی"
        verbose_name_plural = "آیتم‌های سند مالی"




# -----------------------مدل برای کشف قیمت به روز-------------------------------------------------
from django.db import models
from decimal import Decimal
import math

from django.db import models
from decimal import Decimal

from django.db import models
from decimal import Decimal
from django.db.models import F

from django.db import models, transaction
from django.db.models import F
from decimal import Decimal

# --------------------------------------------------------------------
# class ProductPricing(models.Model):
#     product_name = models.CharField(max_length=100, verbose_name="نام کالا", unique=True)
#     highest_purchase_price = models.DecimalField(
#         max_digits=15,
#         decimal_places=2,
#         verbose_name="بالاترین قیمت خرید"
#     )
#     invoice_date = models.CharField(max_length=10, verbose_name="تاریخ فاکتور", blank=True, null=True)
#     invoice_number = models.CharField(max_length=50, verbose_name="شماره فاکتور", blank=True, null=True)
#     adjustment_percentage = models.DecimalField(
#         max_digits=5,
#         decimal_places=2,
#         default=0,
#         verbose_name="درصد تعدیل قیمت خرید"
#     )
#     standard_price = models.DecimalField(
#         max_digits=15,
#         decimal_places=2,
#         verbose_name="قیمت معیار",
#         blank=True, null=True
#     )
#     created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
#     updated_at = models.DateTimeField(auto_now=True, verbose_name="آخرین بروزرسانی")
#
#     class Meta:
#         verbose_name = "قیمت‌گذاری محصول"
#         verbose_name_plural = "قیمت‌گذاری محصولات"
#
#     def save(self, *args, **kwargs):
#         # ابتدا object رو ذخیره می‌کنیم
#         super().save(*args, **kwargs)
#
#         # سپس مستقیماً در دیتابیس آپدیت می‌کنیم
#         self.force_update_standard_price()
#
#     def force_update_standard_price(self):
#         """آپدیت قطعی قیمت معیار با استفاده از transaction"""
#         try:
#             with transaction.atomic():
#                 # محاسبه قیمت جدید
#                 if self.highest_purchase_price is not None and self.adjustment_percentage is not None:
#                     adjustment_amount = self.highest_purchase_price * (self.adjustment_percentage / Decimal('100'))
#                     new_price = self.highest_purchase_price + adjustment_amount
#
#                     # آپدیت مستقیم در دیتابیس
#                     ProductPricing.objects.filter(pk=self.pk).update(
#                         standard_price=new_price
#                     )
#
#                     # رفرش object از دیتابیس
#                     self.refresh_from_db()
#                     print(f"✅ قیمت معیار با موفقیت در دیتابیس ذخیره شد: {self.standard_price}")
#
#         except Exception as e:
#             print(f"❌ خطا در ذخیره‌سازی: {e}")
#
#     def __str__(self):
#         return f"{self.product_name} - {self.standard_price}"


class ProductPricing(models.Model):
    product_name = models.CharField(max_length=100, verbose_name="نام کالا", unique=True)
    highest_purchase_price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name="بالاترین قیمت خرید",
        null=True,
        blank=True,
        default=0
    )
    invoice_date = models.CharField(max_length=10, verbose_name="تاریخ فاکتور", blank=True, null=True)
    invoice_number = models.CharField(max_length=50, verbose_name="شماره فاکتور", blank=True, null=True)
    adjustment_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name="درصد تعدیل قیمت خرید"
    )
    standard_price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name="قیمت معیار",
        blank=True, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="آخرین بروزرسانی")

    class Meta:
        verbose_name = "قیمت‌گذاری محصول"
        verbose_name_plural = "قیمت‌گذاری محصولات"

    def save(self, *args, **kwargs):
        # ابتدا object رو ذخیره می‌کنیم
        super().save(*args, **kwargs)

        # سپس محاسبات را انجام می‌دهیم
        self.force_update_standard_price()

    def force_update_standard_price(self):
        """آپدیت قطعی قیمت معیار با استفاده از transaction"""
        try:
            from django.db import transaction

            with transaction.atomic():
                # محاسبه قیمت جدید - با تبدیل ایمن به Decimal
                if self.highest_purchase_price is not None and self.adjustment_percentage is not None:
                    # تبدیل ایمن به Decimal
                    from decimal import Decimal

                    highest_purchase = Decimal(str(self.highest_purchase_price or 0))
                    adjustment_percent = Decimal(str(self.adjustment_percentage or 0))

                    # محاسبه قیمت معیار
                    adjustment_amount = highest_purchase * (adjustment_percent / Decimal('100'))
                    new_price = highest_purchase + adjustment_amount

                    # آپدیت مستقیم در دیتابیس
                    ProductPricing.objects.filter(pk=self.pk).update(
                        standard_price=new_price
                    )

                    # رفرش object از دیتابیس
                    self.refresh_from_db()
                    print(f"✅ قیمت معیار با موفقیت در دیتابیس ذخیره شد: {self.standard_price}")

        except Exception as e:
            print(f"❌ خطا در ذخیره‌سازی ProductPricing: {e}")

    def __str__(self):
        return f"{self.product_name} - {self.standard_price}"
# ------------------------------------------------------------------------------
from django.db import models
from django.core.validators import RegexValidator  # این خط را اضافه کنید

class PaymentMethod(models.Model):
    PAYMENT_TYPES = [
        ('cash', 'نقدی'),
        ('card', 'کارتخوان'),
        ('bank', 'واریز به حساب'),
        ('cheque', 'چک'),
    ]

    name = models.CharField(max_length=100, verbose_name="نام روش پرداخت")
    payment_type = models.CharField(max_length=10, choices=PAYMENT_TYPES, verbose_name="نوع پرداخت")
    is_default = models.BooleanField(default=False, verbose_name="پیش فرض")
    is_active = models.BooleanField(default=True, verbose_name="فعال")

    # فیلدهای مربوط به کارتخوان
    terminal_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="نام ترمینال")
    account_number = models.CharField(max_length=20, blank=True, null=True, verbose_name="شماره حساب")

    # فیلدهای مربوط به واریز به حساب
    bank_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="نام بانک")
    card_number = models.CharField(
        max_length=16,
        blank=True,
        null=True,
        verbose_name="شماره کارت",
        validators=[
            RegexValidator(
                regex='^[0-9]{16}$',
                message='شماره کارت باید 16 رقم باشد',
                code='invalid_card_number'
            )
        ]
    )
    sheba_number = models.CharField(
        max_length=26,
        blank=True,
        null=True,
        verbose_name="شماره شبا",
        validators=[
            RegexValidator(
                regex='^IR[0-9]{24}$',
                message='شماره شبا باید با IR شروع شده و 24 رقم داشته باشد',
                code='invalid_sheba_number'
            )
        ]
    )
    account_owner = models.CharField(max_length=100, blank=True, null=True, verbose_name="صاحب حساب")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")

    class Meta:
        verbose_name = "روش پرداخت"
        verbose_name_plural = "روش‌های پرداخت"
        ordering = ['-is_default', 'name']

    def __str__(self):
        return f"{self.name} ({self.get_payment_type_display()})"

    def save(self, *args, **kwargs):
        # اگر این روش به عنوان پیش فرض علامت خورده، سایر روش‌ها را از حالت پیش فرض خارج کن
        if self.is_default:
            PaymentMethod.objects.filter(is_default=True).exclude(id=self.id).update(is_default=False)
        super().save(*args, **kwargs)

    def clean(self):
        # غیرفعال کردن اعتبارسنجی اجباری برای کارتخوان
        if self.payment_type == 'bank':
            if not self.bank_name:
                raise ValidationError({'bank_name': 'برای روش پرداخت واریز به حساب، نام بانک الزامی است'})
            if not self.account_number:
                raise ValidationError({'account_number': 'برای روش پرداخت واریز به حساب، شماره حساب الزامی است'})
            if not self.sheba_number:
                raise ValidationError({'sheba_number': 'برای روش پرداخت واریز به حساب، شماره شبا الزامی است'})
            if not self.account_owner:
                raise ValidationError({'account_owner': 'برای روش پرداخت واریز به حساب، نام صاحب حساب الزامی است'})


# ----------------------------------------ثبت هزینه ها----------------------------------------------
from django.db import models
from django.utils import timezone
from io import BytesIO
from PIL import Image
from django.core.files.base import ContentFile
import os

class Expense(models.Model):
    STATUS_CHOICES = [
        ('pending', 'در انتظار تایید'),
        ('approved', 'تایید شده'),
        ('rejected', 'رد شده'),
    ]

    user = models.ForeignKey('cantact_app.accuntmodel', on_delete=models.CASCADE, verbose_name="کاربر ثبت کننده")
    description = models.TextField(max_length=1000, verbose_name="شرح هزینه")
    amount = models.DecimalField(max_digits=12, decimal_places=0, verbose_name="مبلغ هزینه")
    branch = models.ForeignKey('cantact_app.Branch', on_delete=models.CASCADE, verbose_name="شعبه")
    expense_date = models.DateField(auto_now_add=True, verbose_name="تاریخ ثبت")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending', verbose_name="وضعیت تایید")

    class Meta:
        verbose_name = "هزینه"
        verbose_name_plural = "هزینه‌ها"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.firstname} {self.user.lastname} - {self.amount} - {self.expense_date}"

class ExpenseImage(models.Model):
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(
        upload_to='expense_receipts/%Y/%m/%d/',
        verbose_name="عکس فاکتور",
        null=True,
        blank=True,
        default=None
    )
    compressed_image = models.ImageField(
        upload_to='compressed_receipts/%Y/%m/%d/',
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(default=timezone.now, verbose_name="تاریخ ایجاد")

    def compress_image(self):
        if self.image:
            try:
                img = Image.open(self.image)
                max_size = (800, 800)
                if img.height > max_size[0] or img.width > max_size[1]:
                    img.thumbnail(max_size, Image.Resampling.LANCZOS)

                img_io = BytesIO()

                if img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')

                img.save(img_io, format='JPEG', quality=60, optimize=True)

                original_name = os.path.splitext(os.path.basename(self.image.name))[0]
                compressed_name = f"compressed_{original_name}.jpg"

                self.compressed_image.save(
                    compressed_name,
                    ContentFile(img_io.getvalue()),
                    save=False
                )

            except Exception as e:
                print(f"Error compressing image: {e}")
                self.compressed_image = self.image

    def save(self, *args, **kwargs):
        if self.image and (not self.compressed_image or self.image != self.compressed_image):
            self.compress_image()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "عکس فاکتور"
        verbose_name_plural = "عکس‌های فاکتور"
        ordering = ['-created_at']

    def __str__(self):
        return f"Receipt for {self.expense}"


class StockTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('purchase', 'خرید'),
        ('sale', 'فروش'),
        ('return', 'مرجوعی'),
        ('adjustment', 'تعدیل'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    quantity = models.IntegerField()
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        db_table = 'stock_transactions'