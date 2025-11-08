from django.urls import path
from . import views

app_name = 'sync_app'

urlpatterns = [
    path('control-panel/', views.sync_control_panel, name='control_panel'),
    path('execute-command/', views.execute_command, name='execute_command'),
    path('command-status/', views.get_command_status, name='command_status'),
    path('stats/', views.get_sync_stats, name='sync_stats'),
    path('transfer-progress/', views.get_transfer_progress, name='transfer_progress'),  # جدید
]