from django.urls import path
from .views import manage_ips, list_ips, add_ip, delete_ip, update_ip, toggle_ip,create_offline_installer

urlpatterns = [
    path('ip_manager/', manage_ips, name='manage_ips'),  # این میشه: /ip/ip_manager/
    path('ip_manager/api/list/', list_ips, name='list_ips'),  # این میشه: /ip/ip_manager/api/list/
    path('ip_manager/api/add/', add_ip, name='add_ip'),  # این میشه: /ip/ip_manager/api/add/
    path('ip_manager/api/delete/<int:ip_id>/', delete_ip, name='delete_ip'),  # این میشه: /ip/ip_manager/api/delete/1/
    path('ip_manager/api/update/<int:ip_id>/', update_ip, name='update_ip'),  # این میشه: /ip/ip_manager/api/update/1/
    path('ip_manager/api/toggle/<int:ip_id>/', toggle_ip, name='toggle_ip'),  # این میشه: /ip/ip_manager/api/toggle/1/
    path('ip-manager/api/create-offline-installer/', create_offline_installer, name='create_offline_installer'),
]