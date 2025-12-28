# cash_management/urls.py
from django.urls import path
from . import views

app_name = 'cash_management'

urlpatterns = [
    # -----------------------------------------------سرمایه گزاری------------------------------------------
    path('investment/', views.investment_registration, name='investment_registration'),
    path('check-melicode/', views.check_melicode, name='check_melicode'),
    path('convert-amount-to-words/', views.convert_amount_to_words, name='convert_amount_to_words'),

    # ----------------------------گزارش سرمایه گزاری------------------------------------------------------------------------

    path('investment-report/', views.investment_report_view, name='investment_report'),

    # ---------------------------تایید پرداخت---------------------------------------------------------------------------

    path('investment/registration/', views.investment_registration, name='investment_registration'),
    path('investment/report/', views.investment_report_view, name='investment_report'),
    path('investment/check-melicode/', views.check_melicode, name='check_melicode'),
    path('investment/convert-amount/', views.convert_amount_to_words, name='convert_amount_to_words'),

    # تقویم و مدیریت روزانه
    path('calendar/', views.calendar_view, name='calendar'),
    path('day-detail/', views.day_detail_view, name='day_detail'),

    # ذخیره اطلاعات
    path('save-branch-cash/', views.save_branch_cash, name='save_branch_cash'),
    path('save-cheque/', views.save_cheque, name='save_cheque'),
    path('save-credit/', views.save_credit, name='save_credit'),
    path('save-investment/', views.save_investment, name='save_investment'),

    # تایید و عملیات
    path('verify-item/', views.verify_item, name='verify_item'),
    path('finalize-day/', views.finalize_day, name='finalize_day'),

    # تنظیمات و مغایرت
    path('add-adjustment/', views.add_adjustment, name='add_adjustment'),
    path('bulk-update/', views.bulk_update, name='bulk_update'),
    path('get-discrepancies/', views.get_discrepancies, name='get_discrepancies'),

    # ------------------------------------------------------گزارش صندوق---------------------------------------
    path('cash-balance-report/', views.cash_balance_report, name='cash_balance_report'),

]