from django.urls import path
from . import views

app_name = 'sync_api'

urlpatterns = [
    path('pull/', views.sync_pull, name='sync_pull'),
    path('receive/', views.receive_change, name='sync_receive'),  # این خط
    path('model-data/', views.sync_model_data, name='sync_model_data'),
    path('branches/', views.sync_branches, name='sync_branches'),
    path('users/', views.sync_users, name='sync_users'),

]