from ip_manager.views import manage_ips, add_ip, delete_ip, update_ip, toggle_ip
from django.urls import path

urlpatterns = [
    # ...
    path('ip-manager/', manage_ips, name='manage_ips'),
    path('api/ip-manager/add/', add_ip, name='add_ip'),
    path('api/ip-manager/delete/<int:ip_id>/', delete_ip, name='delete_ip'),
    path('api/ip-manager/update/<int:ip_id>/', update_ip, name='update_ip'),
    path('api/ip-manager/toggle/<int:ip_id>/', toggle_ip, name='toggle_ip'),
]