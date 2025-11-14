from django.urls import path
from . import views

app_name = 'it_app'

urlpatterns = [
    # صفحه اصلی لیست فاکتورها
    path('invoices/', views.invoice_list, name='invoice_list'),

    # ریست کردن تعداد باقیمانده
    path('invoices/reset-remaining/', views.reset_remaining_quantity, name='reset_remaining_quantity'),

    # توزیع ترتیبی فاکتورها
    path('invoices/start-distribution/', views.start_distribution, name='start_distribution'),
    path('invoices/distribute-next/', views.distribute_next_invoice, name='distribute_next_invoice'),
    path('invoices/complete-distribution/', views.complete_distribution, name='complete_distribution'),

    # توزیع قدیمی (برای سازگاری)
    path('invoices/distribute/', views.distribute_inventory, name='distribute_inventory'),

    # مدیریت قیمت‌ها
    path('delete-all-pricing/', views.delete_all_product_pricing, name='delete_all_product_pricing'),

    # مدیریت انبار
    path('clear-inventory/', views.clear_inventory, name='clear_inventory'),
]