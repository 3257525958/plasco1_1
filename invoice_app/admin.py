from django.contrib import admin
from .models import POSDevice, CheckPayment, CreditPayment, Invoicefrosh, InvoiceItemfrosh


@admin.register(POSDevice)
class POSDeviceAdmin(admin.ModelAdmin):
    list_display = ['name', 'account_holder', 'bank_name', 'card_number', 'is_default', 'is_active', 'created_at']
    list_filter = ['is_default', 'is_active', 'bank_name', 'created_at']
    search_fields = ['name', 'account_holder', 'bank_name', 'card_number', 'account_number']
    list_editable = ['is_default', 'is_active']
    readonly_fields = ['created_at']

    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('name', 'is_default', 'is_active')
        }),
        ('اطلاعات حساب', {
            'fields': ('account_holder', 'card_number', 'account_number', 'bank_name')
        }),
        ('تاریخ‌ها', {
            'fields': ('created_at',)
        })
    )


class CheckPaymentAdmin(admin.ModelAdmin):
    list_display = ['invoice', 'owner_full_name', 'check_number', 'amount_display', 'remaining_amount_display',
                    'remaining_payment_method', 'check_date', 'created_at']
    list_filter = ['check_date', 'remaining_payment_method', 'created_at']
    search_fields = ['owner_name', 'owner_family', 'check_number', 'national_id', 'phone']
    readonly_fields = ['invoice', 'created_at']

    fieldsets = (
        ('اطلاعات فاکتور', {
            'fields': ('invoice',)
        }),
        ('اطلاعات صاحب چک', {
            'fields': ('owner_name', 'owner_family', 'national_id', 'phone', 'address')
        }),
        ('اطلاعات چک', {
            'fields': ('check_number', 'amount', 'check_date')
        }),
        ('پرداخت باقیمانده', {
            'fields': ('remaining_amount', 'remaining_payment_method', 'pos_device')
        }),
        ('تاریخ‌ها', {
            'fields': ('created_at',)
        })
    )

    def owner_full_name(self, obj):
        return f"{obj.owner_name} {obj.owner_family}"

    owner_full_name.short_description = 'نام کامل صاحب چک'

    def amount_display(self, obj):
        return f"{obj.amount:,} تومان"

    amount_display.short_description = 'مبلغ چک'

    def remaining_amount_display(self, obj):
        return f"{obj.remaining_amount:,} تومان"

    remaining_amount_display.short_description = 'مبلغ باقیمانده'


class CreditPaymentAdmin(admin.ModelAdmin):
    list_display = ['invoice', 'customer_full_name', 'phone', 'credit_amount_display',
                    'remaining_amount_display', 'remaining_payment_method', 'due_date', 'created_at']
    list_filter = ['due_date', 'created_at', 'remaining_payment_method']
    search_fields = ['customer_name', 'customer_family', 'national_id', 'phone']
    readonly_fields = ['invoice', 'created_at']

    fieldsets = (
        ('اطلاعات فاکتور', {
            'fields': ('invoice',)
        }),
        ('اطلاعات مشتری', {
            'fields': ('customer_name', 'customer_family', 'national_id', 'phone', 'address')
        }),
        ('اطلاعات نسیه', {
            'fields': ('credit_amount', 'due_date')
        }),
        ('پرداخت باقیمانده', {
            'fields': ('remaining_amount', 'remaining_payment_method', 'pos_device')
        }),
        ('تاریخ‌ها', {
            'fields': ('created_at',)
        })
    )

    def customer_full_name(self, obj):
        return f"{obj.customer_name} {obj.customer_family}"

    customer_full_name.short_description = 'نام کامل مشتری'

    def credit_amount_display(self, obj):
        return f"{obj.credit_amount:,} تومان"

    credit_amount_display.short_description = 'مبلغ نسیه'

    def remaining_amount_display(self, obj):
        return f"{obj.remaining_amount:,} تومان"

    remaining_amount_display.short_description = 'مبلغ باقیمانده'


@admin.register(InvoiceItemfrosh)
class InvoiceItemfroshAdmin(admin.ModelAdmin):
    list_display = ['invoice', 'product', 'quantity', 'price_display', 'discount_display',
                    'total_price_display', 'standard_price_display']
    list_filter = ['invoice__branch', 'invoice__created_at']
    search_fields = ['product__product_name', 'invoice__serial_number']
    readonly_fields = ['invoice', 'product', 'quantity', 'price', 'total_price', 'standard_price', 'discount']

    def price_display(self, obj):
        return f"{obj.price:,} تومان"

    price_display.short_description = 'قیمت واحد'

    def discount_display(self, obj):
        return f"{obj.discount:,} تومان"

    discount_display.short_description = 'تخفیف'

    def total_price_display(self, obj):
        return f"{obj.total_price:,} تومان"

    total_price_display.short_description = 'قیمت کل'

    def standard_price_display(self, obj):
        return f"{obj.standard_price:,} تومان"

    standard_price_display.short_description = 'قیمت معیار'

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Invoicefrosh)
class InvoicefroshAdmin(admin.ModelAdmin):
    list_display = ['serial_number', 'branch', 'customer_name', 'total_amount',
                    'total_standard_price_display', 'total_profit',  # 🔴 اضافه شده
                    'payment_method', 'is_finalized', 'is_paid', 'created_at']
    list_filter = ['branch', 'payment_method', 'is_finalized', 'is_paid', 'created_at']
    readonly_fields = ['serial_number', 'created_at', 'total_profit', 'total_standard_price']  # 🔴 اضافه شده

    fieldsets = (
        ('اطلاعات پایه', {
            'fields': ('serial_number', 'branch', 'created_by', 'created_at')
        }),
        ('اطلاعات پرداخت', {
            'fields': ('payment_method', 'pos_device', 'total_amount',
                       'total_without_discount', 'discount', 'paid_amount',
                       'is_finalized', 'is_paid', 'payment_date')
        }),
        ('اطلاعات مشتری', {
            'fields': ('customer_name', 'customer_phone')
        }),
        ('سود فاکتور', {
            'fields': ('total_profit', 'total_standard_price')  # 🔴 اضافه شده
        }),
    )

    # 🔴 متد جدید برای نمایش در لیست
    def total_standard_price_display(self, obj):
        return f"{obj.total_standard_price:,} تومان"

    total_standard_price_display.short_description = 'مجموع قیمت معیار'
# @admin.register(Invoicefrosh)
# class InvoicefroshAdmin(admin.ModelAdmin):
#     list_display = ['serial_number', 'branch', 'customer_name', 'total_amount',
#                     'total_profit', 'payment_method', 'is_finalized', 'is_paid', 'created_at']
#     list_filter = ['branch', 'payment_method', 'is_finalized', 'is_paid', 'created_at']
#     readonly_fields = ['serial_number', 'created_at', 'total_profit']
#
#     fieldsets = (
#         ('اطلاعات پایه', {
#             'fields': ('serial_number', 'branch', 'created_by', 'created_at')
#         }),
#         ('اطلاعات پرداخت', {
#             'fields': ('payment_method', 'pos_device', 'total_amount',
#                        'total_without_discount', 'discount', 'paid_amount',
#                        'is_finalized', 'is_paid', 'payment_date')
#         }),
#         ('اطلاعات مشتری', {
#             'fields': ('customer_name', 'customer_phone')
#         }),
#         ('سود فاکتور', {
#             'fields': ('total_profit',)
#         }),
#     )


# ثبت مدل‌ها با کلاس‌های Admin سفارشی
admin.site.register(CheckPayment, CheckPaymentAdmin)
admin.site.register(CreditPayment, CreditPaymentAdmin)

# تنظیمات مربوط به ادمین
admin.site.site_header = 'سیستم مدیریت فروش'
admin.site.site_title = 'پنل مدیریت فروش'
admin.site.index_title = 'مدیریت فروش و فاکتورها'