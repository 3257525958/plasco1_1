from django.contrib import admin
from django.utils import timezone
from jdatetime import date as jdate
from .models import (
    POSDevice, Invoicefrosh, InvoiceItemfrosh,
    CheckPayment, CreditPayment, CashPayment, POSTransaction
)


# ==================== فیلترهای سفارشی ====================

class JalaliDateFilter(admin.SimpleListFilter):
    title = 'تاریخ شمسی'
    parameter_name = 'jalali_date'

    def lookups(self, request, model_admin):
        return (
            ('today', 'امروز'),
            ('yesterday', 'دیروز'),
            ('this_week', 'این هفته'),
            ('this_month', 'این ماه'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'today':
            today = jdate.today()
            return queryset.filter(created_at__date=today.togregorian())
        elif self.value() == 'yesterday':
            yesterday = jdate.today() - jdate.resolution
            return queryset.filter(created_at__date=yesterday.togregorian())
        # سایر فیلترها را می‌توانید اضافه کنید


class PaymentMethodFilter(admin.SimpleListFilter):
    title = 'روش پرداخت'
    parameter_name = 'payment_method'

    def lookups(self, request, model_admin):
        return [
            ('cash', 'نقدی'),
            ('pos', 'دستگاه پوز'),
            ('check', 'چک'),
            ('credit', 'نسیه'),
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(payment_method=self.value())


# ==================== اینلاین‌ها ====================

class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItemfrosh
    extra = 0
    readonly_fields = ['product', 'quantity', 'price', 'total_price', 'standard_price', 'discount']
    can_delete = False

    def has_add_permission(self, request, obj):
        return False


class CheckPaymentInline(admin.StackedInline):
    model = CheckPayment
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj):
        return False


class CreditPaymentInline(admin.StackedInline):
    model = CreditPayment
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj):
        return False


class CashPaymentInline(admin.StackedInline):
    model = CashPayment
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj):
        return False


# ==================== ادمین کلاس‌ها ====================

@admin.register(POSDevice)
class POSDeviceAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'bank_name', 'account_holder', 'card_number',
        'ip_address', 'port', 'is_default', 'is_active', 'created_at'
    ]
    list_filter = ['is_default', 'is_active', 'bank_name', 'created_at']
    search_fields = ['name', 'bank_name', 'account_holder', 'card_number', 'ip_address']
    list_editable = ['is_default', 'is_active']
    readonly_fields = ['created_at']

    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('name', 'is_default', 'is_active')
        }),
        ('اطلاعات بانکی', {
            'fields': ('account_holder', 'card_number', 'account_number', 'bank_name')
        }),
        ('تنظیمات شبکه', {
            'fields': ('ip_address', 'port'),
            'classes': ('collapse',)
        }),
        ('تاریخ‌ها', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )


@admin.register(Invoicefrosh)
class InvoicefroshAdmin(admin.ModelAdmin):
    list_display = [
        'serial_number', 'get_jalali_date', 'get_jalali_time', 'branch',
        'customer_name', 'total_amount', 'total_profit', 'payment_method_display',
        'is_paid', 'is_finalized', 'created_by'
    ]

    list_filter = [
        PaymentMethodFilter,
        'is_paid',
        'is_finalized',
        'branch',
        'created_at',
        JalaliDateFilter
    ]

    search_fields = [
        'serial_number',
        'customer_name',
        'customer_phone',
        'created_by__username',
        'created_by__first_name',
        'created_by__last_name'
    ]

    readonly_fields = [
        'serial_number',
        'created_at',
        'payment_date',
        'total_profit',
        'total_standard_price_display',
        'profit_display'
    ]

    inlines = [
        InvoiceItemInline,
        CheckPaymentInline,
        CreditPaymentInline,
        CashPaymentInline
    ]

    fieldsets = (
        ('اطلاعات اصلی فاکتور', {
            'fields': (
                'serial_number',
                'branch',
                'created_by',
                'created_at'
            )
        }),
        ('اطلاعات مشتری', {
            'fields': (
                'customer_name',
                'customer_phone'
            )
        }),
        ('اطلاعات مالی', {
            'fields': (
                'total_amount',
                'total_without_discount',
                'discount',
                'total_standard_price',
                'total_profit',
                'profit_display',
                'total_standard_price_display'
            )
        }),
        ('وضعیت فاکتور', {
            'fields': (
                'payment_method',
                'pos_device',
                'is_finalized',
                'is_paid',
                'payment_date',
                'paid_amount'
            )
        })
    )

    def payment_method_display(self, obj):
        return obj.get_payment_method_display()

    payment_method_display.short_description = 'روش پرداخت'

    def get_jalali_date(self, obj):
        return obj.get_jalali_date()

    get_jalali_date.short_description = 'تاریخ'
    get_jalali_date.admin_order_field = 'created_at'

    def get_jalali_time(self, obj):
        return obj.get_jalali_time()

    get_jalali_time.short_description = 'زمان'

    def total_standard_price_display(self, obj):
        return obj.total_standard_price_display()

    total_standard_price_display.short_description = 'مجموع قیمت معیار'

    def profit_display(self, obj):
        return obj.profit_display()

    profit_display.short_description = 'سود فاکتور'


@admin.register(InvoiceItemfrosh)
class InvoiceItemfroshAdmin(admin.ModelAdmin):
    list_display = [
        'invoice',
        'product',
        'quantity',
        'price',
        'total_price',
        'standard_price',
        'discount',
        'profit'
    ]

    list_filter = [
        'invoice__branch',
        'invoice__created_at'
    ]

    search_fields = [
        'invoice__serial_number',
        'product__product_name'
    ]

    readonly_fields = ['profit']

    def profit(self, obj):
        profit_amount = (obj.price - obj.standard_price) * obj.quantity - obj.discount
        return f"{profit_amount:,} تومان"

    profit.short_description = 'سود آیتم'


@admin.register(CheckPayment)
class CheckPaymentAdmin(admin.ModelAdmin):
    list_display = [
        'invoice',
        'owner_name',
        'owner_family',
        'check_number',
        'amount',
        'remaining_amount',
        'check_date',
        'created_at'
    ]

    list_filter = [
        'check_date',
        'created_at'
    ]

    search_fields = [
        'invoice__serial_number',
        'owner_name',
        'owner_family',
        'check_number',
        'national_id'
    ]

    readonly_fields = ['created_at']

    fieldsets = (
        ('اطلاعات فاکتور', {
            'fields': ('invoice',)
        }),
        ('اطلاعات صاحب چک', {
            'fields': (
                'owner_name',
                'owner_family',
                'national_id',
                'phone',
                'address'
            )
        }),
        ('اطلاعات چک', {
            'fields': (
                'check_number',
                'amount',
                'check_date'
            )
        }),
        ('پرداخت باقیمانده', {
            'fields': (
                'remaining_amount',
                'remaining_payment_method',
                'pos_device'
            )
        }),
        ('تاریخ‌ها', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )


@admin.register(CreditPayment)
class CreditPaymentAdmin(admin.ModelAdmin):
    list_display = [
        'invoice',
        'customer_name',
        'customer_family',
        'phone',
        'credit_amount',
        'remaining_amount',
        'due_date',
        'created_at'
    ]

    list_filter = [
        'due_date',
        'created_at'
    ]

    search_fields = [
        'invoice__serial_number',
        'customer_name',
        'customer_family',
        'national_id',
        'phone'
    ]

    readonly_fields = ['created_at']

    fieldsets = (
        ('اطلاعات فاکتور', {
            'fields': ('invoice',)
        }),
        ('اطلاعات مشتری', {
            'fields': (
                'customer_name',
                'customer_family',
                'national_id',
                'phone',
                'address'
            )
        }),
        ('اطلاعات نسیه', {
            'fields': (
                'credit_amount',
                'due_date'
            )
        }),
        ('پرداخت باقیمانده', {
            'fields': (
                'remaining_amount',
                'remaining_payment_method',
                'pos_device'
            )
        }),
        ('تاریخ‌ها', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )


@admin.register(CashPayment)
class CashPaymentAdmin(admin.ModelAdmin):
    list_display = [
        'invoice',
        'cash_amount',
        'remaining_amount',
        'remaining_payment_method',
        'pos_device',
        'created_at'
    ]

    list_filter = [
        'remaining_payment_method',
        'created_at'
    ]

    search_fields = [
        'invoice__serial_number',
        'invoice__customer_name'
    ]

    readonly_fields = ['created_at']

    fieldsets = (
        ('اطلاعات فاکتور', {
            'fields': ('invoice',)
        }),
        ('اطلاعات پرداخت نقدی', {
            'fields': (
                'cash_amount',
                'remaining_amount',
                'remaining_payment_method',
                'pos_device'
            )
        }),
        ('تاریخ‌ها', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )


@admin.register(POSTransaction)
class POSTransactionAdmin(admin.ModelAdmin):
    list_display = [
        'transaction_id',
        'branch',
        'amount_rial',
        'amount_toman',
        'pos_ip',
        'status_display',
        'created_at'
    ]

    list_filter = [
        'status',
        'branch',
        'created_at'
    ]

    search_fields = [
        'transaction_id',
        'branch__name',
        'pos_ip',
        'result_message'
    ]

    readonly_fields = [
        'transaction_id',
        'created_at',
        'updated_at'
    ]

    def status_display(self, obj):
        status_dict = dict(POSTransaction.STATUS_CHOICES)
        return status_dict.get(obj.status, obj.status)

    status_display.short_description = 'وضعیت'

    def amount_toman(self, obj):
        return f"{obj.amount_rial // 10:,} تومان"

    amount_toman.short_description = 'مبلغ (تومان)'


# ==================== اکشن‌های سفارشی ====================

def mark_as_paid(modeladmin, request, queryset):
    queryset.update(is_paid=True, payment_date=timezone.now())


mark_as_paid.short_description = "علامت‌گذاری به عنوان پرداخت شده"


def mark_as_finalized(modeladmin, request, queryset):
    queryset.update(is_finalized=True)


mark_as_finalized.short_description = "علامت‌گذاری به عنوان نهایی شده"


def set_default_pos_device(modeladmin, request, queryset):
    # ابتدا همه را غیرپیش‌فرض کنیم
    POSDevice.objects.filter(is_default=True).update(is_default=False)
    # سپس دستگاه انتخاب شده را پیش‌فرض کنیم
    queryset.update(is_default=True)


set_default_pos_device.short_description = "تنظیم به عنوان دستگاه پیش‌فرض"

# اضافه کردن اکشن‌ها به مدل‌ها
InvoicefroshAdmin.actions = [mark_as_paid, mark_as_finalized]
POSDeviceAdmin.actions = [set_default_pos_device]

# ==================== تنظیمات ادمین سایت ====================

admin.site.site_header = "سیستم مدیریت فروش"
admin.site.site_title = "پنل مدیریت فروش"
admin.site.index_title = "خوش آمدید به پنل مدیریت سیستم فروش"