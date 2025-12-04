from django.urls import path
from . import views

app_name = 'invoice_app'

urlpatterns = [
    # 🔴 همه URLها را بدون فاصله اصلاح کنید
    path('create/', views.create_invoice, name='create_invoice'),
    path('manage-pos-devices/', views.manage_pos_devices, name='manage_pos_devices'),
    path('search-product/', views.search_product, name='invoice_search_product'),
    path('add-item/', views.add_item_to_invoice, name='invoice_add_item'),
    path('remove-item/', views.remove_item_from_invoice, name='invoice_remove_item'),
    path('update-quantity/', views.update_item_quantity, name='update_item_quantity'),
    path('update-item-discount/', views.update_item_discount, name='update_item_discount'),
    path('save-customer-info/', views.save_customer_info, name='save_customer_info'),
    path('save-payment-method/', views.save_payment_method, name='save_payment_method'),
    path('save-pos-device/', views.save_pos_device, name='save_pos_device'),
    path('save-check-payment/', views.save_check_payment, name='save_check_payment'),
    path('save-credit-payment/', views.save_credit_payment, name='save_credit_payment'),
    path('save-discount/', views.save_discount, name='save_discount'),
    path('finalize/', views.finalize_invoice, name='finalize_invoice'),
    path('process-pos-payment/', views.process_pos_payment, name='process_pos_payment'),
    path('success/<int:invoice_id>/', views.invoice_success, name='invoice_success'),
    path('print/<int:invoice_id>/', views.invoice_print, name='invoice_print'),
    path('cancel/', views.cancel_invoice, name='invoice_cancel'),
    path('get-summary/', views.get_invoice_summary, name='get_invoice_summary'),
    path('confirm-check-payment/', views.confirm_check_payment, name='confirm_check_payment'),
    path('quick-pos-test/', views.quick_pos_test, name='quick_pos_test'),

    # 🔴 URLهای جدید اضافه کنید
    path('bridge-mapping/', views.bridge_mapping_view, name='bridge_mapping'),
    path('test-bridge-connection/', views.test_bridge_connection, name='test_bridge_connection'),
path('quick-pos-test-api/', views.quick_pos_test_api, name='quick_pos_test_api'),


path('create-pos-transaction/', views.create_pos_transaction, name='create_pos_transaction'),
    path('get-pending-transactions/', views.get_pending_transactions, name='get_pending_transactions'),
    path('update-transaction-status/', views.update_transaction_status, name='update_transaction_status'),
    path('transaction-status/<str:transaction_id>/', views.transaction_status, name='transaction_status'),
    # ------------------------------برای ثبت غیر پوز--------------------------------------------
path('finalize-invoice-non-pos/', views.finalize_invoice_non_pos, name='finalize_invoice_non_pos'),
# 🔴 URLهای گزارش‌گیری فاکتورها
path('report/', views.invoice_report, name='invoice_report'),
path('api/report-data/', views.get_invoice_report_data, name='get_invoice_report_data'),
path('api/export-csv/', views.export_invoice_report_csv, name='export_invoice_report_csv'),
path('api/quick-stats/', views.quick_stats, name='quick_stats'),



    # urls.py - اضافه کردن URL جدید
    path('save-cash-payment/', views.save_cash_payment, name='save_cash_payment'),

# ------------------------------------------بستن فاکتورهای روزانه----------------------------------------
    path('daily/', views.daily_invoices, name='daily_invoices'),
    path('detail/<int:invoice_id>/', views.invoice_detail, name='invoice_detail'),
    path('edit/<int:invoice_id>/', views.edit_invoice, name='edit_invoice'),
    path('delete/<int:invoice_id>/', views.delete_invoice, name='delete_invoice'),
    path('update-status/<int:invoice_id>/', views.update_invoice_status, name='update_invoice_status'),
    path('filter/', views.filter_invoices, name='filter_invoices'),
    path('create/', views.create_invoice, name='create_invoice'),

]