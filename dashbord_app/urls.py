

from django.urls import path
from . import views

urlpatterns = [
    path('sana/froshande/', views.froshande_view, name='froshande'),
    path('sana/froshande/<int:froshande_id>/accounts/', views.froshande_accounts_view, name='froshande_accounts'),
    path('sana/froshande/<int:froshande_id>/edit/', views.froshande_edit_view, name='froshande_edit'),
    path('sana/froshande/<int:froshande_id>/delete/', views.froshande_delete_view, name='froshande_delete'),
    path('sana/froshande/<int:froshande_id>/delete-ajax/', views.froshande_delete_ajax, name='froshande_delete_ajax'),
    path('sana/froshande/list/', views.froshande_list_view, name='froshande_list'),


    path('create-invoice/', views.create_invoice, name='create_invoice'),
    path('search-sellers/', views.search_sellers, name='search_sellers'),
    path('search-products/', views.search_products, name='search_products'),
    path('invoice/<int:invoice_id>/', views.invoice_detail, name='invoice_detail'),
    path('confirm-invoice/', views.confirm_invoice, name='confirm_invoice'),

    path('search-invoices/', views.search_invoices, name='search_invoices'),
    path('edit-invoice/<int:invoice_id>/', views.edit_invoice, name='edit_invoice'),
    path('print-labels/<int:invoice_id>/', views.print_labels, name='print_labels'),


    # path('print-settings/', views.print_settings, name='print_settings'),
    # تغییر مسیر چاپ به پیش‌نمایش
    path('print-preview/<int:invoice_id>/', views.print_preview, name='print_preview_invoice'),
    path('print-preview/', views.print_preview, name='print_preview_inventory'),
    # مسیر تنظیمات چاپ
    path('print-settings/', views.print_settings, name='print_settings'),

    path('usb/',views.usb_view, name='usb'),

    # URLهای جدید برای چاپ سریع لیبل
    path('quick-label-print/', views.quick_label_print, name='quick_label_print'),
    path('generate-label-barcode/', views.generate_label_barcode, name='generate_label_barcode'),
    path('search-products-label/', views.search_products_for_label, name='search_products_label'),
    path('search-branches-label/', views.search_branches_for_label, name='search_branches_label'),

    path('quick-label-print/', views.quick_label_print_page, name='quick_label_print_page'),
    path('search-inventory-label/', views.search_inventory_for_label, name='search_inventory_for_label'),
    path('add-to-print-list/', views.add_to_print_list, name='add_to_print_list'),
    path('get-print-list/', views.get_print_list, name='get_print_list'),
    path('clear-print-list/', views.clear_print_list, name='clear_print_list'),
    path('go-to-print-settings/', views.go_to_print_settings, name='go_to_print_settings'),
    path('print-settings/', views.print_settings, name='print_settings'),

    # مسیرهای جدید برای ویرایش فاکتور
    path('edit-invoice/', views.edit_invoice_page, name='edit_invoice_page'),
    path('search-invoices-for-edit/', views.search_invoices_for_edit, name='search_invoices_for_edit'),
    path('get-invoice-for-edit/', views.get_invoice_for_edit, name='get_invoice_for_edit'),
    path('update-invoice/', views.update_invoice, name='update_invoice'),


]
