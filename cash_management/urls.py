# cash_management/urls.py
from django.urls import path
from . import views

app_name = 'cash_management'

urlpatterns = [
    # صفحات اصلی
    path('cash-inventory/', views.cash_inventory_view, name='cash_inventory'),
    path('expense-registration/', views.expense_registration_view, name='expense_registration'),
    path('expense-payment/', views.expense_payment_view, name='expense_payment'),
    path('discrepancy-review/', views.discrepancy_review_view, name='discrepancy_review'),

    # API endpoints برای AJAX
    path('api/get-cash-data/', views.get_cash_inventory_data, name='get_cash_data'),
    path('api/get-account-data/', views.get_account_inventory_data, name='get_account_data'),  # <- این خط اضافه شود
    path('api/confirm-inventory/', views.confirm_inventory, name='confirm_inventory'),
    path('api/register-investment/', views.register_investment, name='register_investment'),
    path('api/search-investor/', views.search_investor, name='search_investor'),
    path('api/get-credit-accounts/', views.get_credit_accounts, name='get_credit_accounts'),
    path('api/resolve-discrepancy/<int:discrepancy_id>/', views.resolve_discrepancy, name='resolve_discrepancy'),

    # APIهای جدید
    path('api/get-expenses-for-payment/', views.get_expenses_for_payment, name='get_expenses_for_payment'),
    path('api/process-payments/', views.process_payments, name='process_payments'),
    path('api/register-expense/', views.register_expense, name='register_expense'),
    path('api/get-today-expenses/', views.get_today_expenses, name='get_today_expenses'),
    path('api/delete-expense/<int:expense_id>/', views.delete_expense, name='delete_expense'),
    path('api/get-discrepancies/', views.get_discrepancies, name='get_discrepancies'),
    path('api/get-discrepancy/<int:discrepancy_id>/', views.get_discrepancy_detail, name='get_discrepancy_detail'),

    # -----------------------------------------------سرمایه گزاری------------------------------------------
    path('investment/', views.investment_registration, name='investment_registration'),
    path('check-melicode/', views.check_melicode, name='check_melicode'),
    path('convert-amount-to-words/', views.convert_amount_to_words, name='convert_amount_to_words'),

    # ----------------------------گزارش سرمایه گزاری------------------------------------------------------------------------

    path('investment-report/', views.investment_report_view, name='investment_report'),

]