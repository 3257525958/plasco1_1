
from home_app import views
from django.urls import path , include
from django.contrib import admin
from django.conf.urls.static import static
from . import settings
admin.autodiscover()


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('home_app.urls')),
    path('cantact/', include('cantact_app.urls')),
    path('dashbord/', include('dashbord_app.urls')),
    path('account/', include('account_app.urls')),
    path('invoice/', include('invoice_app.urls')),
    path('it/', include('it_app.urls')),
    path('pos-payment/', include('pos_payment.urls')),
    path('api/sync/', include('sync_api.urls')),
    path('sync_app/', include('sync_app.urls')),
    path('sync/', include('sync_app.urls')),

]
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
urlpatterns += static(settings.MEDIA_URL,document_root=settings.MEDIA_ROOT)
