from django.urls import path
from . import views

urlpatterns = [
    path('invoices/', views.invoice_list, name='invoice_list'),
    path('invoices/reset/', views.reset_remaining_quantity, name='reset_remaining_quantity'),
    path('invoices/distribute/', views.distribute_inventory, name='distribute_inventory'),

    path('invoices/distribute-status/<str:task_id>/', views.get_distribution_status, name='get_distribution_status'),

    path('delete-all-product-pricing/', views.delete_all_product_pricing, name='delete_all_product_pricing'),
    path('clear-inventory/', views.clear_inventory, name='clear_inventory'),
]