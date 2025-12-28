from django.contrib import admin
from .models import (
    DailyCashStatus, DailyBranchCash, DailyCheque,
    DailyCredit, DailyInvestment, DailyCashAdjustment,
    Discrepancy, Investment, CashRegister
)

@admin.register(Investment)
class InvestmentAdmin(admin.ModelAdmin):
    list_display = ['investor', 'investment_date', 'amount', 'payment_method', 'is_finalized']
    list_filter = ['is_finalized', 'payment_method', 'investment_date']
    search_fields = ['investor__firstname', 'investor__lastname', 'investor__melicode']

@admin.register(Discrepancy)
class DiscrepancyAdmin(admin.ModelAdmin):
    list_display = ['discrepancy_date', 'item_type', 'description', 'previous_amount',
                   'new_amount', 'difference', 'review_status', 'resolution_status']
    list_filter = ['review_status', 'resolution_status', 'item_type', 'discrepancy_date']
    search_fields = ['description', 'reason', 'reviewer_melicode', 'responder_melicode']

@admin.register(CashRegister)
class CashRegisterAdmin(admin.ModelAdmin):
    list_display = ['branch', 'date', 'cash_amount', 'pos_amount', 'cheque_amount',
                   'credit_amount', 'investment_amount', 'is_verified']
    list_filter = ['is_verified', 'branch', 'date']
    search_fields = ['branch__name']

@admin.register(DailyCashStatus)
class DailyCashStatusAdmin(admin.ModelAdmin):
    list_display = ['date', 'get_jalali_date', 'is_verified', 'verified_by', 'verified_at']
    list_filter = ['is_verified', 'date']
    search_fields = ['date']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(DailyBranchCash)
class DailyBranchCashAdmin(admin.ModelAdmin):
    list_display = ['daily_status', 'branch', 'cash_amount', 'pos_amount', 'is_verified', 'created_by']
    list_filter = ['is_verified', 'branch', 'daily_status__date']
    search_fields = ['branch__name']

@admin.register(DailyCheque)
class DailyChequeAdmin(admin.ModelAdmin):
    list_display = ['cheque_number', 'branch', 'cheque_amount', 'due_date', 'status', 'is_verified']
    list_filter = ['status', 'is_verified', 'branch', 'due_date']
    search_fields = ['cheque_number', 'bank_name', 'invoice__id']

@admin.register(DailyCredit)
class DailyCreditAdmin(admin.ModelAdmin):
    list_display = ['customer_name', 'branch', 'credit_amount', 'due_date', 'status', 'is_verified']
    list_filter = ['status', 'is_verified', 'branch', 'due_date']
    search_fields = ['customer_name', 'customer_phone']

@admin.register(DailyInvestment)
class DailyInvestmentAdmin(admin.ModelAdmin):
    list_display = ['investor_name', 'investment_amount', 'payment_method', 'is_verified', 'created_by']
    list_filter = ['is_verified', 'payment_method', 'is_returned']
    search_fields = ['investor_name', 'investor_melicode']

@admin.register(DailyCashAdjustment)
class DailyCashAdjustmentAdmin(admin.ModelAdmin):
    list_display = ['daily_status', 'adjustment_type', 'amount', 'is_positive', 'created_by', 'created_at']
    list_filter = ['is_positive', 'adjustment_type']
    search_fields = ['description', 'adjustment_type']