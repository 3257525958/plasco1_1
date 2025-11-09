from django.urls import path, include
from django.contrib import admin
from django.conf.urls.static import static
from . import settings

# ایمپورت ویوها
from control_panel.views import control_panel, set_mode
from offline_ins.views import offline_install, install_step, offline_success
from home_app.views import home_def  # تابع home شما
from offline_ins.views import switch_to_offline

urlpatterns = [
    # ... سایر URLها
    path('offline-system/', switch_to_offline, name='offline_system'),
]

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home_def, name='home'),  # صفحه اصلی با تابع home_def شما
    path('control-panel/', control_panel, name='control_panel'),
    path('set-mode/', set_mode, name='set_mode'),
    path('offline/install/', offline_install, name='offline_install'),
    path('offline/install-step/', install_step, name='install_step'),
    path('offline/success/', offline_success, name='offline_success'),

    # سایر URLهای اپ‌های شما
    path('cantact/', include('cantact_app.urls')),
    path('dashbord/', include('dashbord_app.urls')),
    path('account/', include('account_app.urls')),
    path('invoice/', include('invoice_app.urls')),
    path('it/', include('it_app.urls')),
    path('pos-payment/', include('pos_payment.urls')),
    path('api/sync/', include('sync_api.urls')),
    path('sync_app/', include('sync_app.urls')),
    path('sync/', include('sync_app.urls')),
    path('switch-to-offline/', switch_to_offline, name='switch_to_offline'),
]

USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)