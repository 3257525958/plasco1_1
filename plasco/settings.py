#
# # -------------------------لوکال هاست---------------------------------
# """
# Django settings for plasco project.
# برای اجرا روی کامپیوترهای داخلی شرکت - حالت آفلاین
# """
#
# from pathlib import Path
# import os
#
# BASE_DIR = Path(__file__).resolve().parent.parent
#
# # حالت آفلاین
# IS_OFFLINE_MODE = True
# SECRET_KEY = 'django-insecure-9a=faq-)zl&%@!5(9t8!0r(ar)&()3l+hc#a)+-!eh$-ljkdh@'
# DEBUG = True
#
# # لیست IPهای مجاز برای حالت آفلاین
# OFFLINE_ALLOWED_IPS = ['192.168.1.172', '192.168.1.157', '127.0.0.1', 'localhost', '192.168.1.100', '192.168.1.101']
# ALLOWED_HOSTS = OFFLINE_ALLOWED_IPS + ['plasmarket.ir', 'www.plasmarket.ir']
#
# print("🟢 اجرا در حالت آفلاین - ديتابيس محلي (Slave)")
#
# INSTALLED_APPS = [
#     'django.contrib.admin',
#     'django.contrib.auth',
#     'django.contrib.contenttypes',
#     'django.contrib.sessions',
#     'django.contrib.messages',
#     'django.contrib.staticfiles',
#     'rest_framework',
#     'rest_framework.authtoken',
#     'corsheaders',
#     'account_app.apps.AccountAppConfig',
#     'dashbord_app.apps.DashbordAppConfig',
#     'cantact_app.apps.CantactAppConfig',
#     'invoice_app.apps.InvoiceAppConfig',
#     'it_app.apps.ItAppConfig',
#     'pos_payment.apps.PosPaymentConfig',
#     'sync_app',
#     'sync_api',
#     'control_panel',
#     'offline_ins',
#     'ip_manager'
# ]
#
# MIDDLEWARE = [
#     'corsheaders.middleware.CorsMiddleware',
#     'django.middleware.security.SecurityMiddleware',
#     'django.contrib.sessions.middleware.SessionMiddleware',
#     'django.middleware.common.CommonMiddleware',
#     'django.middleware.csrf.CsrfViewMiddleware',
#     'django.contrib.auth.middleware.AuthenticationMiddleware',
#     'django.contrib.messages.middleware.MessageMiddleware',
#     'django.middleware.clickjacking.XFrameOptionsMiddleware',
#     'plasco.middleware.ControlPanelMiddleware',  # این خط اضافه شد
# ]
# ROOT_URLCONF = 'plasco.urls'
#
# TEMPLATES = [
#     {
#         'BACKEND': 'django.template.backends.django.DjangoTemplates',
#         'DIRS': [BASE_DIR / 'templates'],
#         'APP_DIRS': True,
#         'OPTIONS': {
#             'context_processors': [
#                 'django.template.context_processors.request',
#                 'django.contrib.auth.context_processors.auth',
#                 'django.contrib.messages.context_processors.messages',
#             ],
#         },
#     },
# ]
#
# WSGI_APPLICATION = 'plasco.wsgi.application'
#
# # دیتابیس SQLite برای حالت آفلاین
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db_offline.sqlite3',
#     }
# }
#
# AUTH_PASSWORD_VALIDATORS = [
#     {
#         'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
#     },
#     {
#         'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
#     },
#     {
#         'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
#     },
#     {
#         'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
#     },
# ]
#
# LANGUAGE_CODE = 'fa-ir'
# TIME_ZONE = 'Asia/Tehran'
# USE_I18N = True
# USE_TZ = True
#
# STATIC_URL = '/static/'
# MEDIA_URL = '/media/'
# STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
# STATIC_ROOT = '/static/'
# MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
#
# DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
#
# # تنظیمات همگام‌سازی
# SYNC_INTERVAL = 60
# ONLINE_SERVER_URL = "https://plasmarket.ir"
# OFFLINE_MODE = True
# ALLOWED_OFFLINE_IPS = OFFLINE_ALLOWED_IPS
#
# # ⚠️ اضافه کردن این خط جدید برای غیرفعال کردن سرویس خودکار
# SYNC_AUTO_START = True  # غیرفعال کردن سرویس سینک خودکار

# # ----------------------------------------سرور هاست-----------------------------------
"""
Django settings for plasco project.
سرور اصلی - دیتابیس Master
"""

from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

IS_OFFLINE_MODE = False
SECRET_KEY = 'django-insecure-9a=faq-)zl&%@!5(9t8!0r(ar)&()3l+hc#a)+-!eh$-ljkdh@'

DEBUG = True
ALLOWED_HOSTS = ['http://plasmarket.ir','plasmarket.ir','www.plasmarket.ir','https://plasmarket.ir','192.168.1.157']
CSRF_TRUSTED_ORIGINS = ["https://plasmarket.ir",'http://plasmarket.ir','https://www.plasmarket.ir','http://www.plasmarket.ir']

print("🔵 اجرا در حالت آنلاین - ديتابيس اصلی (Master)")

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'account_app.apps.AccountAppConfig',
    'dashbord_app.apps.DashbordAppConfig',
    'cantact_app.apps.CantactAppConfig',
    'invoice_app.apps.InvoiceAppConfig',
    'it_app.apps.ItAppConfig',
    'pos_payment.apps.PosPaymentConfig',
    'sync_app',
    'sync_api',
    'control_panel',
'offline_ins',
'ip_manager'
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # 'plasco.middleware.ControlPanelMiddleware',  # این خط اضافه شد
]
ROOT_URLCONF = 'plasco.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'plasco.wsgi.application'

# دیتابیس MySQL برای سرور اصلی
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'plascodavor_db',
        'USER': 'root',
        'PASSWORD': 'zh21oYmLXiINj!Es3Rtq',
        'HOST': 'plascodata1-ayh-service',
        'PORT': '3306',
        'OPTIONS': {
            'charset': 'utf8mb4',
        }
    }
}

# بقیه تنظیمات...
SESSION_ENGINE = 'django.contrib.sessions.backends.db'  # یا 'django.contrib.sessions.backends.cache'
SESSION_COOKIE_AGE = 3600  # 1 hour
SESSION_SAVE_EVERY_REQUEST = True

LANGUAGE_CODE = 'fa-ir'
TIME_ZONE = 'Asia/Tehran'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
MEDIA_URL = '/media/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT = '/static/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# تنظیمات همگام‌سازی
SYNC_INTERVAL = 60
ONLINE_SERVER_URL = "https://plasmarket.ir"
OFFLINE_MODE = False

