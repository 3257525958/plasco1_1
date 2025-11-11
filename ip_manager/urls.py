from django.urls import path
from .views import manage_ips, list_ips, add_ip, delete_ip, update_ip, toggle_ip

urlpatterns = [
    path('', manage_ips, name='manage_ips'),  # حذف ip_manager/ از ابتدا
    path('api/list/', list_ips, name='list_ips'),
    path('api/add/', add_ip, name='add_ip'),
    path('api/delete/<int:ip_id>/', delete_ip, name='delete_ip'),
    path('api/update/<int:ip_id>/', update_ip, name='update_ip'),
    path('api/toggle/<int:ip_id>/', toggle_ip, name='toggle_ip'),
    path('ip-manager/api/create-offline-installer/', create_offline_installer, name='create_offline_installer'),
]