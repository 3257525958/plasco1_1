from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
import jdatetime
from invoice_app.models import Invoicefrosh, Paymentnumber
from cantact_app.models import Branch, accuntmodel

User = get_user_model()

# مدل سرمایه‌گذاری
class Investment(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'نقدی'),
        ('bank_transfer', 'واریز به حساب'),
    ]

    investor = models.ForeignKey(accuntmodel, on_delete=models.CASCADE, verbose_name="سرمایه‌گذار")
    investment_date = models.DateField(verbose_name="تاریخ سرمایه‌گذاری")
    amount = models.BigIntegerField(verbose_name="مبلغ (تومان)")
    amount_letters = models.CharField(max_length=500, verbose_name="مبلغ به حروف")
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, verbose_name="روش پرداخت")
    payment_account = models.ForeignKey(Paymentnumber, on_delete=models.SET_NULL, null=True, blank=True,
                                        verbose_name="حساب بانکی")
    is_finalized = models.BooleanField(default=False, verbose_name="در انتظار تایید")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ثبت")

    class Meta:
        verbose_name = "سرمایه‌گذاری"
        verbose_name_plural = "سرمایه‌گذاری‌ها"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.investor.firstname} {self.investor.lastname} - {self.amount:,} تومان"


# مدل مغایرت
class Discrepancy(models.Model):
    REVIEW_STATUS_CHOICES = [
        ('pending', 'بررسی مجدد لازم'),
        ('reviewed_rejected', 'بررسی شد و تایید نشد'),
        ('reviewed_approved', 'بررسی شد و تایید شد'),
    ]

    RESOLUTION_CHOICES = [
        ('unresolved', 'رفع نشده'),
        ('resolved', 'رفع شده'),
    ]

    ITEM_TYPE_CHOICES = [
        ('invoice_cash', 'فاکتور نقدی'),
        ('invoice_pos', 'فاکتور پوز'),
        ('invoice_check', 'چک'),
        ('invoice_credit', 'نسیه'),
        ('investment', 'سرمایه‌گذاری'),
    ]

    # اطلاعات عمومی
    discrepancy_date = models.DateField(verbose_name='تاریخ مغایرت')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')

    # ارتباط با شعبه
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, verbose_name='شعبه', null=True, blank=True)

    # مبالغ
    previous_amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='مبلغ قبل از تغییر')
    new_amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='مبلغ پس از تغییر')
    difference = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='مبلغ تفاوت', default=0)

    # نوع مورد
    item_type = models.CharField(max_length=20, choices=ITEM_TYPE_CHOICES, verbose_name='نوع مورد')

    # ارتباط با مدل اصلی
    invoice = models.ForeignKey(Invoicefrosh, on_delete=models.SET_NULL, null=True, blank=True,
                                verbose_name='فاکتور مربوطه')
    investment = models.ForeignKey('Investment', on_delete=models.SET_NULL, null=True, blank=True,
                                   verbose_name='سرمایه‌گذاری مربوطه')
    item_id = models.PositiveIntegerField(verbose_name='شناسه مورد', null=True, blank=True)
    description = models.CharField(max_length=200, verbose_name='توضیح مختصر', blank=True)

    # علت مغایرت
    reason = models.TextField(max_length=1000, verbose_name='علت مغایرت')

    # اطلاعات افراد
    reviewer_melicode = models.CharField(max_length=10, verbose_name='کد ملی رسیدگی کننده')
    responder_melicode = models.CharField(max_length=10, verbose_name='کد ملی پاسخ دهنده')

    # وضعیت‌ها
    review_status = models.CharField(
        max_length=20,
        choices=REVIEW_STATUS_CHOICES,
        default='pending',
        verbose_name='وضعیت بررسی'
    )
    resolution_status = models.CharField(
        max_length=20,
        choices=RESOLUTION_CHOICES,
        default='unresolved',
        verbose_name='وضعیت رفع مغایرت'
    )

    # کاربران
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_discrepancies',
        verbose_name='ایجاد کننده'
    )
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_discrepancies',
        verbose_name='بررسی کننده'
    )

    # زمان‌های بررسی
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name='زمان بررسی')
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name='زمان رفع')

    # یادداشت‌ها
    notes = models.TextField(blank=True, verbose_name='یادداشت‌ها')

    class Meta:
        verbose_name = 'مغایرت'
        verbose_name_plural = 'مغایرت‌ها'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        # محاسبه خودکار تفاوت مبالغ
        self.difference = self.new_amount - self.previous_amount

        # اگر مبلغ تغییر کرده و آیتم مربوطه وجود دارد
        if self.difference != 0 and self.item_id:
            # برای فاکتورها
            if self.item_type.startswith('invoice_'):
                try:
                    invoice = Invoicefrosh.objects.get(id=self.item_id)
                    # به‌روزرسانی مبلغ فاکتور فقط اگر وضعیت تایید شده باشد
                    if self.review_status == 'reviewed_approved':
                        invoice.total_amount = self.new_amount
                        invoice.save()
                except Invoicefrosh.DoesNotExist:
                    pass

            # برای سرمایه‌گذاری‌ها
            elif self.item_type == 'investment':
                try:
                    investment = Investment.objects.get(id=self.item_id)
                    if self.review_status == 'reviewed_approved':
                        investment.amount = self.new_amount
                        investment.save()
                except Investment.DoesNotExist:
                    pass

        super().save(*args, **kwargs)

    def __str__(self):
        return f'مغایرت {self.get_item_type_display()} - {self.discrepancy_date}'


# مدل صندوق روزانه
class CashRegister(models.Model):
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, null=True, blank=True)
    date = models.DateField()
    cash_amount = models.DecimalField(max_digits=15, decimal_places=0, default=0)
    pos_amount = models.DecimalField(max_digits=15, decimal_places=0, default=0)
    cheque_amount = models.DecimalField(max_digits=15, decimal_places=0, default=0)
    credit_amount = models.DecimalField(max_digits=15, decimal_places=0, default=0)
    investment_amount = models.DecimalField(max_digits=15, decimal_places=0, default=0)
    cheque_status = models.CharField(max_length=20, choices=[
        ('pending', 'در انتظار'),
        ('passed', 'پاس شده'),
        ('returned', 'برگشت خورده'),
    ], default='pending', verbose_name='وضعیت چک')
    credit_status = models.CharField(max_length=20, choices=[
        ('pending', 'در انتظار'),
        ('paid', 'پرداخت شده'),
        ('delayed', 'معوق'),
    ], default='pending', verbose_name='وضعیت نسیه')

    # سرمایه‌گذاری
    investment_returned = models.BooleanField(default=False, verbose_name='برگشت خورده')

    # وضعیت تایید
    is_verified = models.BooleanField(default=False, verbose_name='تایید شده')
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                    verbose_name='تایید کننده')
    verified_at = models.DateTimeField(null=True, blank=True, verbose_name='زمان تایید')

    # اطلاعات ثبت
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                   related_name='created_cash_registers', verbose_name='ایجاد کننده')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'صندوق روزانه'
        verbose_name_plural = 'صندوق‌های روزانه'
        unique_together = ['branch', 'date']
        ordering = ['-date', 'branch__name']

    def __str__(self):
        jalali = jdatetime.date.fromgregorian(date=self.date)
        return f"صندوق {self.branch.name} - {jalali.strftime('%Y/%m/%d')}"

    def get_jalali_date(self):
        jalali = jdatetime.date.fromgregorian(date=self.date)
        return jalali.strftime('%Y/%m/%d')

    def total_amount(self):
        return self.cash_amount + self.pos_amount + self.cheque_amount + self.credit_amount + self.investment_amount


# مدل‌های اصلی سیستم
class DailyCashStatus(models.Model):
    """وضعیت کلی روز"""
    date = models.DateField(verbose_name='تاریخ', unique=True)
    is_verified = models.BooleanField(default=False, verbose_name='تایید شده')
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                    blank=True, verbose_name='تایید کننده')
    verified_at = models.DateTimeField(null=True, blank=True, verbose_name='زمان تایید')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                   blank=True, related_name='created_daily_statuses',
                                   verbose_name='ایجاد کننده')

    class Meta:
        verbose_name = 'وضعیت روز'
        verbose_name_plural = 'وضعیت روزها'
        ordering = ['-date']

    def __str__(self):
        jalali = jdatetime.date.fromgregorian(date=self.date)
        return f"وضعیت روز {jalali.strftime('%Y/%m/%d')} - {'تایید شده' if self.is_verified else 'تایید نشده'}"

    def get_jalali_date(self):
        jalali = jdatetime.date.fromgregorian(date=self.date)
        return jalali.strftime('%Y/%m/%d')


class DailyBranchCash(models.Model):
    """گردش نقدی و پوز هر شعبه در هر روز"""
    daily_status = models.ForeignKey(DailyCashStatus, on_delete=models.CASCADE,
                                     related_name='branch_cashes', verbose_name='وضعیت روز')
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, verbose_name='شعبه')

    # مبالغ نقدی
    cash_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                      verbose_name='مبلغ نقدی')
    pos_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                     verbose_name='مبلغ پوز')

    # وضعیت تایید
    is_verified = models.BooleanField(default=False, verbose_name='تایید شده')
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                    blank=True, verbose_name='تایید کننده')
    verified_at = models.DateTimeField(null=True, blank=True, verbose_name='زمان تایید')

    # اطلاعات ثبت
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                   related_name='created_branch_cashes', verbose_name='ایجاد کننده')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'گردش نقدی شعبه'
        verbose_name_plural = 'گردش نقدی شعب'
        unique_together = ['daily_status', 'branch']
        ordering = ['branch__name']

    def __str__(self):
        return f"{self.branch.name} - {self.daily_status.get_jalali_date()}"

    def total_amount(self):
        return self.cash_amount + self.pos_amount


class DailyCheque(models.Model):
    """چک‌های سررسید شده در هر روز"""
    CHEQUE_STATUS = [
        ('pending', 'در انتظار'),
        ('passed', 'پاس شده'),
        ('returned', 'برگشت خورده'),
        ('blocked', 'مسدود شده'),
    ]

    daily_status = models.ForeignKey(DailyCashStatus, on_delete=models.CASCADE,
                                     related_name='cheques', verbose_name='وضعیت روز')
    invoice = models.ForeignKey(Invoicefrosh, on_delete=models.CASCADE,
                                verbose_name='فاکتور مربوطه')
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, verbose_name='شعبه')

    # اطلاعات چک
    cheque_amount = models.DecimalField(max_digits=15, decimal_places=2,
                                        verbose_name='مبلغ چک')
    cheque_number = models.CharField(max_length=50, verbose_name='شماره چک')
    due_date = models.DateField(verbose_name='تاریخ سررسید')
    bank_name = models.CharField(max_length=100, verbose_name='نام بانک')

    # وضعیت چک
    status = models.CharField(max_length=20, choices=CHEQUE_STATUS,
                              default='pending', verbose_name='وضعیت')
    destination_account = models.CharField(max_length=100, blank=True,
                                           verbose_name='حساب مقصد')
    passed_date = models.DateField(null=True, blank=True, verbose_name='تاریخ پاس شدن')
    return_reason = models.TextField(blank=True, verbose_name='علت برگشت')

    # وضعیت تایید
    is_verified = models.BooleanField(default=False, verbose_name='تایید شده')
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                    blank=True, verbose_name='تایید کننده')
    verified_at = models.DateTimeField(null=True, blank=True, verbose_name='زمان تایید')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'چک روز'
        verbose_name_plural = 'چک‌های روز'
        ordering = ['due_date']

    def __str__(self):
        return f"چک {self.cheque_number} - {self.branch.name}"


class DailyCredit(models.Model):
    """نسیه‌های سررسید شده در هر روز"""
    CREDIT_STATUS = [
        ('pending', 'در انتظار'),
        ('paid', 'پرداخت شده'),
        ('delayed', 'معوق'),
        ('forgiven', 'بخشوده شده'),
    ]

    daily_status = models.ForeignKey(DailyCashStatus, on_delete=models.CASCADE,
                                     related_name='credits', verbose_name='وضعیت روز')
    invoice = models.ForeignKey(Invoicefrosh, on_delete=models.CASCADE,
                                verbose_name='فاکتور مربوطه')
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, verbose_name='شعبه')

    # اطلاعات نسیه
    credit_amount = models.DecimalField(max_digits=15, decimal_places=2,
                                        verbose_name='مبلغ نسیه')
    customer_name = models.CharField(max_length=100, verbose_name='نام مشتری')
    customer_phone = models.CharField(max_length=15, blank=True, verbose_name='تلفن مشتری')
    due_date = models.DateField(verbose_name='تاریخ سررسید')

    # وضعیت نسیه
    status = models.CharField(max_length=20, choices=CREDIT_STATUS,
                              default='pending', verbose_name='وضعیت')
    paid_date = models.DateField(null=True, blank=True, verbose_name='تاریخ پرداخت')
    payment_method = models.CharField(max_length=50, blank=True, verbose_name='روش پرداخت')
    notes = models.TextField(blank=True, verbose_name='یادداشت')

    # وضعیت تایید
    is_verified = models.BooleanField(default=False, verbose_name='تایید شده')
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                    blank=True, verbose_name='تایید کننده')
    verified_at = models.DateTimeField(null=True, blank=True, verbose_name='زمان تایید')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'نسیه روز'
        verbose_name_plural = 'نسیه‌های روز'
        ordering = ['due_date']

    def __str__(self):
        return f"نسیه {self.customer_name} - {self.branch.name}"


class DailyInvestment(models.Model):
    """سرمایه‌گذاری‌های هر روز"""
    PAYMENT_METHODS = [
        ('cash', 'نقدی'),
        ('bank', 'بانکی'),
        ('cheque', 'چک'),
        ('other', 'سایر'),
    ]

    daily_status = models.ForeignKey(DailyCashStatus, on_delete=models.CASCADE,
                                     related_name='investments', verbose_name='وضعیت روز')

    # اطلاعات سرمایه‌گذار
    investor_name = models.CharField(max_length=100, verbose_name='نام سرمایه‌گذار')
    investor_melicode = models.CharField(max_length=10, verbose_name='کد ملی سرمایه‌گذار')
    investor_phone = models.CharField(max_length=15, blank=True, verbose_name='تلفن سرمایه‌گذار')

    # اطلاعات سرمایه‌گذاری
    investment_amount = models.DecimalField(max_digits=15, decimal_places=2,
                                            verbose_name='مبلغ سرمایه‌گذاری')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS,
                                      verbose_name='روش پرداخت')
    destination_account = models.CharField(max_length=100, blank=True,
                                           verbose_name='حساب مقصد')
    receipt_number = models.CharField(max_length=50, blank=True, verbose_name='شماره رسید')

    # وضعیت سرمایه‌گذاری
    is_returned = models.BooleanField(default=False, verbose_name='برگشت خورده')
    return_date = models.DateField(null=True, blank=True, verbose_name='تاریخ برگشت')
    return_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                        verbose_name='مبلغ برگشتی')
    return_reason = models.TextField(blank=True, verbose_name='علت برگشت')

    # وضعیت تایید
    is_verified = models.BooleanField(default=False, verbose_name='تایید شده')
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                    blank=True, verbose_name='تایید کننده')
    verified_at = models.DateTimeField(null=True, blank=True, verbose_name='زمان تایید')

    # اطلاعات ثبت
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                   related_name='created_investments', verbose_name='ایجاد کننده')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'سرمایه‌گذاری روز'
        verbose_name_plural = 'سرمایه‌گذاری‌های روز'
        ordering = ['-created_at']

    def __str__(self):
        return f"سرمایه‌گذاری {self.investor_name} - {self.investment_amount}"


class DailyCashAdjustment(models.Model):
    """تغییرات و تنظیمات دستی روزانه"""
    daily_status = models.ForeignKey(DailyCashStatus, on_delete=models.CASCADE,
                                     related_name='adjustments', verbose_name='وضعیت روز')

    # اطلاعات تغییر
    adjustment_type = models.CharField(max_length=50, verbose_name='نوع تغییر')
    description = models.TextField(verbose_name='توضیحات')
    amount = models.DecimalField(max_digits=15, decimal_places=2,
                                 verbose_name='مبلغ تغییر')
    is_positive = models.BooleanField(default=True, verbose_name='مثبت')

    # اطلاعات ثبت
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                   verbose_name='ایجاد کننده')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'تنظیم روز'
        verbose_name_plural = 'تنظیمات روز'
        ordering = ['-created_at']

    def __str__(self):
        sign = '+' if self.is_positive else '-'
        return f"{sign}{self.amount} - {self.adjustment_type}"


class ItemVerificationStatus(models.Model):
    """مدل ثبت وضعیت تایید هر آیتم"""
    ITEM_TYPES = [
        ('branch_cash', 'نقدی شعبه'),
        ('branch_pos', 'پوز شعبه'),
        ('investment', 'سرمایه‌گذاری'),
        ('cheque', 'چک'),
        ('credit', 'نسیه'),
    ]

    daily_status = models.ForeignKey(DailyCashStatus, on_delete=models.CASCADE, related_name='item_verifications')
    item_type = models.CharField(max_length=20, choices=ITEM_TYPES)
    item_id = models.PositiveIntegerField()  # ID آیتم در جدول مربوطه

    calculated_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    user_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'وضعیت تایید آیتم'
        verbose_name_plural = 'وضعیت تایید آیتم‌ها'
        unique_together = ['daily_status', 'item_type', 'item_id']

    def __str__(self):
        return f"{self.get_item_type_display()} - {self.item_id}"