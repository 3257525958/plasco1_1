from django.contrib import admin
from .models import InventoryCount

@admin.register(InventoryCount)
class InventoryCountAdmin(admin.ModelAdmin):
    list_display = ['product_name', 'branch', 'quantity','counter', 'created_at','is_new','barcode_data','selling_price','profit_percentage']
    list_filter = ['branch', 'is_new', 'count_date']
    search_fields = ['product_name', 'counter__username']

from account_app.models import FinancialDocument,FinancialDocumentItem

admin.site.register(FinancialDocument)
admin.site.register(FinancialDocumentItem)
# admin.site.register(InvoiceItem)

from django.contrib import admin
from .models import ProductPricing


@admin.register(ProductPricing)
class ProductPricingAdmin(admin.ModelAdmin):
    # نمایش تمام فیلدها در لیست
    list_display = [
        'product_name',
        'highest_purchase_price',
        'standard_price',
        'adjustment_percentage',
        'invoice_number',
        'invoice_date',
        'created_at',
        'updated_at'
    ]

    # غیرفعال کردن جستجو
    search_fields = []

    # غیرفعال کردن فیلترها
    list_filter = []

    # ترتیب نمایش موارد (بر اساس تاریخ به روزرسانی نزولی)
    ordering = ['-updated_at']

    # تعداد آیتم‌های نمایش داده شده در هر صفحه (مقدار زیاد برای نمایش همه)
    list_per_page = 1000

    # فیلدهای غیرقابل ویرایش
    readonly_fields = [
        'created_at',
        'updated_at',
        'standard_price'
    ]

    # گروه‌بندی فیلدها در صفحه ویرایش
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': (
                'product_name',
                'highest_purchase_price',
                'adjustment_percentage',
                'standard_price'
            )
        }),
        ('اطلاعات فاکتور', {
            'fields': (
                'invoice_number',
                'invoice_date'
            )
        }),
        ('تاریخ‌ها', {
            'fields': (
                'created_at',
                'updated_at'
            )
        }),
    )

    # غیرفعال کردن امکان حذف
    def has_delete_permission(self, request, obj=None):
        return False

    # غیرفعال کردن امکان افزودن مورد جدید از طریق ادمین
    def has_add_permission(self, request):
        return False

    # غیرفعال کردن امکان تغییر
    def has_change_permission(self, request, obj=None):
        return False

# ----------------------------------ثبت هزینه ها--------------------------------------------------------------
from django.contrib import admin
from .models import Expense, ExpenseImage

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ['user', 'amount', 'branch', 'expense_date', 'created_at']
    list_filter = ['branch', 'expense_date']
    search_fields = ['user__firstname', 'user__lastname', 'description']
    readonly_fields = ['created_at']

@admin.register(ExpenseImage)
class ExpenseImageAdmin(admin.ModelAdmin):
    list_display = ['expense', 'image']
    list_filter = ['expense__branch']
    search_fields = ['expense__user__firstname', 'expense__user__lastname']

# -------------------------------------------------تاریخجه پرینت لیبل-----------------------------------------------
# account_app/admin.py
from django.contrib import admin
from .models import ProductLabelSetting, LabelPrintItem


class LabelPrintItemInline(admin.TabularInline):
    """اینلاین برای نمایش آیتم‌های چاپ"""
    model = LabelPrintItem
    extra = 0
    readonly_fields = ['print_date']
    can_delete = False


@admin.register(ProductLabelSetting)
class ProductLabelSettingAdmin(admin.ModelAdmin):
    list_display = [
        'product_name',
        'barcode',
        'branch',
        'allow_print'
    ]

    list_filter = [
        'branch',
        'allow_print'
    ]

    search_fields = [
        'product_name',
        'barcode'
    ]

    inlines = [LabelPrintItemInline]


@admin.register(LabelPrintItem)
class LabelPrintItemAdmin(admin.ModelAdmin):
    list_display = [
        'label_setting',
        'print_quantity',
        'user',
        'print_date'
    ]

    list_filter = [
        'print_date',
        'user'
    ]

    readonly_fields = ['print_date']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False