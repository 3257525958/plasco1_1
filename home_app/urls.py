from django.urls import path

from home_app import views

urlpatterns = [
    path('', views.detect_installation, name='installation_detection'),
    path('check-offline-installation/', views.check_offline_installation, name='check_offline_installation'),
    path('start-offline-installation/', views.start_offline_installation, name='start_offline_installation'),
    ]
