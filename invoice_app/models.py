

from django.db import models
from django.contrib.auth.models import User
from jdatetime import datetime as jdatetime
from django.utils import timezone
from decimal import Decimal
from account_app.models import Branch, PaymentMethod, InventoryCount, ProductPricing

class POSDevice(models.Model):
    name = models.CharField(max_length=100, verbose_name="نام دستگاه")
    account_holder = models.CharField(max_length=100, verbose_name="نام صاحب حساب")
    card_number = models.CharField(max_length=16, verbose_name="شماره کارت")
    account_number = models.CharField(max_length=50, verbose_name="شماره حساب")
    bank_name = models.CharField(max_length=100, verbose_name="نام بانک")
    ip_address = models.GenericIPAddressField(verbose_name="آدرس IP", default='192.168.1.157')  # فیلد جدید
    port = models.IntegerField(verbose_name="پورت", default=1362)  # فیلد جدید
    is_default = models.BooleanField(default=False, verbose_name="پیش فرض")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "دستگاه پوز"
        verbose_name_plural = "دستگاه‌های پوز"

    def __str__(self):
        return f"{self.name} - {self.bank_name} - {self.ip_address}:{self.port}"

    def save(self, *args, **kwargs):
        if self.is_default:
            POSDevice.objects.filter(is_default=True).exclude(id=self.id).update(is_default=False)
        elif not POSDevice.objects.filter(is_default=True).exists():
            self.is_default = True
        super().save(*args, **kwargs)

class Paymentnumber(models.Model):
    name = models.CharField(max_length=100, verbose_name="نام دستگاه")
    account_holder = models.CharField(max_length=100, verbose_name="نام صاحب حساب")
    card_number = models.CharField(max_length=16, verbose_name="شماره کارت")
    account_number = models.CharField(max_length=50, verbose_name="شماره حساب")
    bank_name = models.CharField(max_length=100, verbose_name="نام بانک")
    ip_address = models.GenericIPAddressField(verbose_name="آدرس IP", default='192.168.1.157')  # فیلد جدید
    port = models.IntegerField(verbose_name="پورت", default=1362)  # فیلد جدید
    is_default = models.BooleanField(default=False, verbose_name="پیش فرض")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "دستگاه پوز"
        verbose_name_plural = "دستگاه‌های پوز"

    def __str__(self):
        return f"{self.name} - {self.bank_name} - {self.ip_address}:{self.port}"

    # def save(self, *args, **kwargs):
    #     if self.is_default:
    #         POSDevice.objects.filter(is_default=True).exclude(id=self.id).update(is_default=False)
    #     elif not POSDevice.objects.filter(is_default=True).exists():
    #         self.is_default = True
    #     super().save(*args, **kwargs)
    def save(self, *args, **kwargs):
        if self.is_default:
            Paymentnumber.objects.filter(is_default=True).exclude(id=self.id).update(is_default=False)
        elif not Paymentnumber.objects.filter(is_default=True).exists():
            self.is_default = True
        super().save(*args, **kwargs)

class Invoicefrosh(models.Model):
    PAYMENT_METHODS = [
        ('cash', 'نقدی'),
        ('pos', 'دستگاه پوز'),
        ('check', 'چک'),
        ('credit', 'نسیه'),
    ]

    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, verbose_name="شعبه")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="ایجاد کننده")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    payment_date = models.DateTimeField(null=True, blank=True, verbose_name="تاریخ پرداخت")
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHODS, default='pos', verbose_name="روش پرداخت")
    pos_device = models.ForeignKey(POSDevice, on_delete=models.SET_NULL, null=True, blank=True,
                                   verbose_name="دستگاه پوز")
    total_amount = models.PositiveIntegerField(default=0, verbose_name="مبلغ کل")
    total_without_discount = models.PositiveIntegerField(default=0, verbose_name="مبلغ بدون تخفیف")
    discount = models.PositiveIntegerField(default=0, verbose_name="تخفیف")
    is_finalized = models.BooleanField(default=False, verbose_name="نهایی شده")
    is_paid = models.BooleanField(default=False, verbose_name="پرداخت شده")
    customer_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="نام خریدار")
    customer_phone = models.CharField(max_length=15, blank=True, null=True, verbose_name="تلفن خریدار")
    serial_number = models.CharField(max_length=20, unique=True, blank=True, null=True, verbose_name="شماره سریال")
    paid_amount = models.PositiveIntegerField(default=0, verbose_name="مبلغ پرداخت شده")

    # فیلد جدید برای مجموع قیمت معیار
    total_standard_price = models.PositiveIntegerField(default=0, verbose_name="مجموع قیمت معیار")

    # فیلد سود که در مدل محاسبه می‌شود
    total_profit = models.PositiveIntegerField(default=0, verbose_name="سود فاکتور")

    class Meta:
        verbose_name = "فاکتور"
        verbose_name_plural = "فاکتورها"
        ordering = ['-created_at']

    def __str__(self):
        return f"فاکتور {self.id} - {self.branch.name}"

    def save(self, *args, **kwargs):
        if not self.serial_number:
            now = timezone.now()
            self.serial_number = now.strftime('%Y%m%d%H%M%S')

        if self.is_paid and not self.payment_date:
            self.payment_date = timezone.now()

        if self.total_amount and self.discount:
            self.total_without_discount = self.total_amount + self.discount
        else:
            self.total_without_discount = self.total_amount

        # 🔴 محاسبه سود در مدل: مبلغ کل منهای مجموع قیمت معیار
        self.total_profit = max(0, self.total_amount - self.total_standard_price)

        super().save(*args, **kwargs)

    def get_jalali_date(self):
        return jdatetime.fromgregorian(datetime=self.created_at).strftime('%Y/%m/%d')

    def get_jalali_time(self):
        return jdatetime.fromgregorian(datetime=self.created_at).strftime('%H:%M')

    def get_payment_method_display(self):
        return dict(self.PAYMENT_METHODS).get(self.payment_method, 'نامشخص')

    # متد برای نمایش سود
    def profit_display(self):
        return f"{self.total_profit:,} تومان"

    profit_display.short_description = "سود فاکتور"

    # متد برای نمایش مجموع قیمت معیار
    def total_standard_price_display(self):
        return f"{self.total_standard_price:,} تومان"

    total_standard_price_display.short_description = "مجموع قیمت معیار"

class InvoiceItemfrosh(models.Model):
    invoice = models.ForeignKey(Invoicefrosh, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(InventoryCount, on_delete=models.CASCADE, verbose_name="کالا")
    quantity = models.PositiveIntegerField(default=1, verbose_name="تعداد")
    price = models.PositiveIntegerField(verbose_name="قیمت واحد")
    total_price = models.PositiveIntegerField(verbose_name="قیمت کل")
    standard_price = models.PositiveIntegerField(verbose_name="قیمت معیار", default=0)
    discount = models.PositiveIntegerField(default=0, verbose_name="تخفیف")

    class Meta:
        verbose_name = "آیتم فاکتور"
        verbose_name_plural = "آیتم‌های فاکتور"

    def __str__(self):
        return f"{self.product.product_name} - {self.quantity}"

class CheckPayment(models.Model):
    invoice = models.OneToOneField('Invoicefrosh', on_delete=models.CASCADE, related_name='check_payment')
    owner_name = models.CharField(max_length=100, verbose_name="نام صاحب چک")
    owner_family = models.CharField(max_length=100, verbose_name="نام خانوادگی صاحب چک")
    national_id = models.CharField(max_length=10, verbose_name="کد ملی")
    address = models.TextField(verbose_name="آدرس")
    phone = models.CharField(max_length=15, verbose_name="تلفن")
    check_number = models.CharField(max_length=50, verbose_name="شماره چک")
    amount = models.PositiveIntegerField(verbose_name="مبلغ چک")
    remaining_amount = models.PositiveIntegerField(verbose_name="مبلغ باقیمانده", default=0)
    remaining_payment_method = models.CharField(max_length=10, choices=Invoicefrosh.PAYMENT_METHODS, default='cash', verbose_name="روش پرداخت باقیمانده")
    pos_device = models.ForeignKey(POSDevice, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="دستگاه پوز برای باقیمانده")
    check_date = models.DateField(verbose_name="تاریخ چک")
    created_at = models.DateTimeField(auto_now_add=True)


# models.py - اصلاح مدل CreditPayment
class CreditPayment(models.Model):
    invoice = models.OneToOneField('Invoicefrosh', on_delete=models.CASCADE, related_name='credit_payment')
    customer_name = models.CharField(max_length=100, verbose_name="نام")
    customer_family = models.CharField(max_length=100, verbose_name="نام خانوادگی")
    phone = models.CharField(max_length=15, verbose_name="تلفن")
    address = models.TextField(verbose_name="آدرس")
    national_id = models.CharField(max_length=10, verbose_name="کد ملی")
    due_date = models.DateField(verbose_name="تاریخ سررسید")

    # فیلدهای جدید مشابه چک
    credit_amount = models.PositiveIntegerField(verbose_name="مبلغ نسیه", default=0)
    remaining_amount = models.PositiveIntegerField(verbose_name="مبلغ باقیمانده", default=0)
    remaining_payment_method = models.CharField(max_length=10, choices=Invoicefrosh.PAYMENT_METHODS, default='cash',
                                                verbose_name="روش پرداخت باقیمانده")
    pos_device = models.ForeignKey(POSDevice, on_delete=models.SET_NULL, null=True, blank=True,
                                   verbose_name="دستگاه پوز برای باقیمانده")

    created_at = models.DateTimeField(auto_now_add=True)


# invoice_app/models.py (بخش اصلاح شده)

from django.db import models
from django.contrib.auth.models import User
from jdatetime import datetime as jdatetime
from django.utils import timezone


class POSTransaction(models.Model):
    STATUS_CHOICES = [
        ('pending', 'در انتظار'),
        ('processing', 'در حال پردازش'),
        ('success', 'موفق'),
        ('failed', 'ناموفق'),
        ('timeout', 'Timeout'),
    ]

    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    amount_rial = models.BigIntegerField(verbose_name="مبلغ به ریال")
    pos_ip = models.CharField(max_length=20, verbose_name="IP دستگاه پوز")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    result_message = models.TextField(blank=True, null=True, verbose_name="پیام نتیجه")
    transaction_id = models.CharField(max_length=100, unique=True, verbose_name="شناسه تراکنش")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "تراکنش پوز"
        verbose_name_plural = "تراکنش‌های پوز"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.transaction_id} - {self.branch.name} - {self.amount_rial} ریال"


# models.py - اضافه کردن مدل CashPayment
class CashPayment(models.Model):
    invoice = models.OneToOneField('Invoicefrosh', on_delete=models.CASCADE, related_name='cash_payment')
    cash_amount = models.PositiveIntegerField(verbose_name="مبلغ نقدی", default=0)
    remaining_amount = models.PositiveIntegerField(verbose_name="مبلغ باقیمانده", default=0)
    remaining_payment_method = models.CharField(max_length=10, choices=Invoicefrosh.PAYMENT_METHODS, default='pos',
                                                verbose_name="روش پرداخت باقیمانده")
    pos_device = models.ForeignKey(POSDevice, on_delete=models.SET_NULL, null=True, blank=True,
                                   verbose_name="دستگاه پوز برای باقیمانده")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "پرداخت نقدی"
        verbose_name_plural = "پرداخت‌های نقدی"

    def __str__(self):
        return f"پرداخت نقدی - فاکتور {self.invoice.id}"

# ------------------------------------------مرجوعی------------------------------------------------------------------------------------


class ReturnLog(models.Model):
    """لاگ مرجوع کالا"""
    invoice = models.ForeignKey('Invoicefrosh', on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='return_logs', verbose_name="فاکتور")
    returned_by = models.ForeignKey('auth.User', on_delete=models.CASCADE, verbose_name="مرجوع کننده")
    return_amount = models.PositiveIntegerField(verbose_name="مبلغ مرجوع", default=0)
    return_profit = models.PositiveIntegerField(verbose_name="سود مرجوع", default=0)
    reason = models.TextField(verbose_name="دلیل مرجوع", blank=True, null=True)
    return_data = models.JSONField(verbose_name="داده‌های مرجوع", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ مرجوع")

    class Meta:
        verbose_name = "لاگ مرجوع"
        verbose_name_plural = "لاگ‌های مرجوع"
        ordering = ['-created_at']

    def __str__(self):
        return f"مرجوع {self.return_amount} - فاکتور {self.invoice.id if self.invoice else 'حذف شده'}"

    def get_jalali_date(self):
        return jdatetime.fromgregorian(datetime=self.created_at).strftime('%Y/%m/%d')

    def get_jalali_time(self):
        return jdatetime.fromgregorian(datetime=self.created_at).strftime('%H:%M')

