from django.urls import path
from . import views

urlpatterns = [
    path('invoices/', views.invoice_list, name='invoice_list'),
    path('invoices/reset/', views.reset_remaining_quantity, name='reset_remaining_quantity'),
    path('invoices/distribute/', views.distribute_inventory, name='distribute_inventory'),
    path('invoices/check-progress/', views.check_distribution_progress, name='check_distribution_progress'),

    path('delete-all-product-pricing/', views.delete_all_product_pricing, name='delete_all_product_pricing'),
    path('clear-inventory/', views.clear_inventory, name='clear_inventory'),
]