

from django.urls import path
from . import views
# app_name = 'account_app'


urlpatterns = [
    path('inventory/', views.inventory_management, name='inventory_management'),


    path('get-branches/', views.get_branches, name='get_branches'),
    path('search-products/', views.search_products, name='search_products'),
    path('check-product/', views.check_product, name='check_product'),
    path('update-inventory-count/', views.UpdateInventoryCount.as_view(), name='update_inventory_count'),
    path('store-invoice-items/', views.StoreInvoiceItems.as_view(), name='store_invoice_items'),
    path('print-invoice/', views.print_invoice_view, name='print_invoice'),

    # path('admin/print-invoice/<int:invoice_id>/', admin_views.admin_print_invoice, name='admin_print_invoice'),

    path('get-branches/', views.get_branches, name='get_branches'),
    path('search-products/', views.search_products, name='search_products'),
    path('check-product/', views.check_product, name='check_product'),
    path('update-inventory-count/', views.UpdateInventoryCount.as_view(), name='update_inventory_count'),
    path('store-invoice-items/', views.StoreInvoiceItems.as_view(), name='store_invoice_items'),
    path('search_invoices/', views.search_invoices, name='search_invoices'),
    path('get_invoice_details/', views.get_invoice_details, name='get_invoice_details'),


# -----------------------مالی-------------------------------------------
path('invoice-status/<int:invoice_id>/', views.invoice_status, name='invoice_status'),


path('store-invoice-items/', views.StoreInvoiceItems.as_view(), name='store_invoice_items'),
# path('update-product-pricing/', views.UpdateProductPricing.as_view(), name='update_product_pricing'),

    path('search-branches-pricing/', views.search_branches_pricing, name='search_branches_pricing'),
    path('get-branch-products/', views.get_branch_products, name='get_branch_products'),
    # path('search-products-pricing/', views.search_products_pricing, name='search_products_pricing'),
    path('update-product-pricing/', views.update_product_pricing, name='update_product_pricing'),
    path('update-all-product-pricing/', views.update_all_product_pricing, name='update_all_product_pricing'),
    path('pricing-management/', views.pricing_management, name='pricing_management'),


# --------------------url-----------------------
    path('payment-methods/', views.payment_method_list, name='payment_method_list'),
    path('payment-methods/create/', views.payment_method_create, name='payment_method_create'),
    path('payment-methods/<int:pk>/update/', views.payment_method_update, name='payment_method_update'),
    path('payment-methods/<int:pk>/delete/', views.payment_method_delete, name='payment_method_delete'),
    path('payment-methods/<int:pk>/toggle-active/', views.payment_method_toggle_active,
         name='payment_method_toggle_active'),
    path('payment-methods/<int:pk>/set-default/', views.set_default_payment_method, name='set_default_payment_method'),
    path('check-auth/', views.check_auth_status, name='check_auth_status'),
    path('session-test/', views.session_test, name='session_test'),


    # ---------------------انبارگردانی-------------
path('search-branches-count/', views.search_branches_count, name='search_branches_count'),
path('search-products-count/', views.search_products_count, name='search_products_count'),
path('get-product-details/', views.get_product_details, name='get_product_details'),
# ----------------------------ثبت هزینه ها--------------------------------------------------------------------
    path('expense/create/', views.expense_create, name='expense_create'),
    path('expense/list/', views.expense_list, name='expense_list'),
    path('expense/detail/<int:pk>/', views.expense_detail, name='expense_detail'),
    path('expense/delete/<int:pk>/', views.delete_expense, name='delete_expense'),
    path('expense/delete-image/', views.delete_expense_image, name='delete_expense_image'),
# --------------------------------------چاپ لیبل-------------------------------------------------------------
    path('label/generator/', views.label_generator, name='label_generator'),
    path('label/search-products/', views.search_products_for_label, name='search_products_for_label'),
    path('label/add-to-cart/', views.add_product_to_label_cart, name='add_product_to_label_cart'),
    path('label/remove-from-cart/', views.remove_from_label_cart, name='remove_from_label_cart'),
    path('label/get-cart/', views.get_label_cart, name='get_label_cart'),
    path('label/update-quantity/', views.update_cart_quantity, name='update_cart_quantity'),
    path('label/clear-cart/', views.clear_label_cart, name='clear_label_cart'),
    path('label/settings/', views.label_settings, name='label_settings'),
    path('label/print/', views.label_print, name='label_print'),

]

