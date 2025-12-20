# cash_management/models.py
from django.db import models
from django.contrib.auth.models import User
from jdatetime import datetime as jdatetime_datetime
from invoice_app.models import Invoicefrosh, CreditPayment, Branch, POSDevice
from cantact_app.models import accuntmodel


class DiscrepancyLog(models.Model):
    """مدل ثبت مغایرت‌های مالی"""
    DISCREPANCY_STATUS = [
        ('pending', 'در انتظار بررسی'),
        ('reviewed', 'بررسی شده'),
        ('resolved', 'رفع شده'),
    ]

    discrepancy_date = models.DateField(verbose_name="تاریخ مغایرت")
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="تایید کننده",
                             related_name='discrepancy_creator')
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, verbose_name="شعبه", null=True, blank=True)
    investor = models.ForeignKey(accuntmodel, on_delete=models.CASCADE, verbose_name="سرمایه گذار", null=True,
                                 blank=True)
    old_amount = models.PositiveIntegerField(verbose_name="مبلغ قبل از تغییر")
    new_amount = models.PositiveIntegerField(verbose_name="مبلغ بعد از تغییر")
    difference = models.IntegerField(verbose_name="مقدار تفاوت", default=0)
    description = models.TextField(verbose_name="دلیل مغایرت", blank=True)
    status = models.CharField(max_length=20, choices=DISCREPANCY_STATUS, default='pending', verbose_name="وضعیت بررسی")
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='discrepancy_reviewer', verbose_name="بررسی کننده")
    review_date = models.DateTimeField(null=True, blank=True, verbose_name="تاریخ بررسی")
    review_notes = models.TextField(verbose_name="یادداشت بررسی", blank=True)
    resolution_notes = models.TextField(verbose_name="یادداشت رفع مغایرت", blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان ایجاد")

    class Meta:
        verbose_name = "لاگ مغایرت"
        verbose_name_plural = "لاگ‌های مغایرت"
        ordering = ['-discrepancy_date', '-created_at']

    def __str__(self):
        if self.branch:
            return f"مغایرت شعبه {self.branch.name} - {self.discrepancy_date}"
        elif self.investor:
            return f"مغایرت {self.investor.firstname} {self.investor.lastname} - {self.discrepancy_date}"
        return f"مغایرت - {self.discrepancy_date}"

    def save(self, *args, **kwargs):
        self.difference = self.new_amount - self.old_amount
        super().save(*args, **kwargs)




# cash_management/models.py
# به جای استفاده از مدل Expense جداگانه، از مدل موجود در account_app استفاده می‌کنیم
# یا نام مدل را تغییر می‌دهیم

# راه حل 1: تغییر نام مدل به CashExpense
class CashExpense(models.Model):  # نام تغییر کرد
    EXPENSE_TYPES = [
        ('operational', 'عملیاتی'),
        ('personnel', 'پرسنلی'),
        ('administrative', 'اداری'),
        ('other', 'متفرقه'),
    ]

    PAYMENT_STATUS = [
        ('pending', 'در انتظار پرداخت'),
        ('paid', 'پرداخت شده'),
        ('cancelled', 'لغو شده'),
    ]

    title = models.CharField(max_length=200, verbose_name="عنوان هزینه")
    expense_type = models.CharField(max_length=20, choices=EXPENSE_TYPES, default='operational',
                                    verbose_name="نوع هزینه")
    amount = models.PositiveIntegerField(verbose_name="مبلغ (تومان)")
    expense_date = models.DateField(verbose_name="تاریخ هزینه")
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, verbose_name="شعبه", null=True, blank=True,
                               related_name='cash_expenses')  # اضافه کردن related_name
    payment_method = models.CharField(max_length=10, choices=Invoicefrosh.PAYMENT_METHODS, default='cash',
                                      verbose_name="روش پرداخت")
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending',
                                      verbose_name="وضعیت پرداخت")
    description = models.TextField(verbose_name="توضیحات", blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="ثبت کننده")
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name="زمان پرداخت")
    attachment = models.FileField(upload_to='expense_attachments/', null=True, blank=True, verbose_name="ضمیمه")

    class Meta:
        verbose_name = "هزینه نقدی"
        verbose_name_plural = "هزینه‌های نقدی"
        ordering = ['-expense_date', '-created_at']

    def __str__(self):
        return f"{self.title} - {self.amount:,} تومان"

    def get_jalali_date(self):
        return jdatetime_datetime.fromgregorian(date=self.expense_date).strftime('%Y/%m/%d')

class CashInventory(models.Model):
    """مدل موجودی روزانه صندوق"""
    INVENTORY_TYPES = [
        ('cash', 'نقدی'),
        ('account', 'حساب'),
    ]

    inventory_date = models.DateField(verbose_name="تاریخ موجودی")
    inventory_type = models.CharField(max_length=10, choices=INVENTORY_TYPES, default='cash', verbose_name="نوع موجودی")
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, verbose_name="شعبه", null=True, blank=True)
    investor = models.ForeignKey(accuntmodel, on_delete=models.CASCADE, verbose_name="سرمایه گذار", null=True,
                                 blank=True)
    calculated_amount = models.PositiveIntegerField(verbose_name="مبلغ محاسبه شده", default=0)
    actual_amount = models.PositiveIntegerField(verbose_name="مبلغ واقعی", default=0)
    is_confirmed = models.BooleanField(default=False, verbose_name="تایید شده")
    confirmed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="تایید کننده")
    confirmed_at = models.DateTimeField(null=True, blank=True, verbose_name="زمان تایید")
    notes = models.TextField(verbose_name="یادداشت", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "موجودی صندوق"
        verbose_name_plural = "موجودی‌های صندوق"
        unique_together = ['inventory_date', 'inventory_type', 'branch', 'investor']
        ordering = ['-inventory_date']

    def __str__(self):
        if self.branch:
            return f"{self.branch.name} - {self.inventory_date} - {self.get_inventory_type_display()}"
        elif self.investor:
            return f"{self.investor.firstname} {self.investor.lastname} - {self.inventory_date} - {self.get_inventory_type_display()}"
        return f"{self.inventory_date} - {self.get_inventory_type_display()}"

    def save(self, *args, **kwargs):
        # اگر مبلغ واقعی تغییر کرد و با مبلغ محاسبه شده متفاوت بود، مغایرت ثبت شود
        if self.pk and self.actual_amount != self.calculated_amount and not self.is_confirmed:
            old_amount = self.calculated_amount
            new_amount = self.actual_amount
            if old_amount != new_amount:
                DiscrepancyLog.objects.create(
                    discrepancy_date=self.inventory_date,
                    user=self.confirmed_by if self.confirmed_by else None,
                    branch=self.branch,
                    investor=self.investor,
                    old_amount=old_amount,
                    new_amount=new_amount,
                    description=f"مغایرت در موجودی صندوق - تاریخ {self.inventory_date}"
                )
        super().save(*args, **kwargs)



# ------------------------------صفحه ورود سرمایه-------------------------------------------------
from django.db import models
from cantact_app.models import accuntmodel
from invoice_app.models import Paymentnumber


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
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ثبت")

    class Meta:
        verbose_name = "سرمایه‌گذاری"
        verbose_name_plural = "سرمایه‌گذاری‌ها"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.investor.firstname} {self.investor.lastname} - {self.amount:,} تومان"