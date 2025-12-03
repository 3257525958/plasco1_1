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
# SESSION_ENGINE = 'django.contrib.sessions.backends.db'  # حتماً از دیتابیس استفاده کنید
# SESSION_COOKIE_NAME = 'plasco_session_id'
# SESSION_COOKIE_AGE = 3600 * 24  # 24 ساعت
# SESSION_EXPIRE_AT_BROWSER_CLOSE = True
# SESSION_COOKIE_SECURE = True  # برای HTTPS
# SESSION_COOKIE_HTTPONLY = True
# SESSION_COOKIE_SAMESITE = 'Lax'
# SESSION_SAVE_EVERY_REQUEST = True

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
# ALLOWED_HOSTS = ['http://plasmarket.ir','plasmarket.ir','www.plasmarket.ir','https://plasmarket.ir','192.168.1.157']
# CSRF_TRUSTED_ORIGINS = ["https://plasmarket.ir",'http://plasmarket.ir','https://www.plasmarket.ir','http://www.plasmarket.ir']
ALLOWED_HOSTS = [
    'plasmarket.ir',      # دامنه اصلی
    'www.plasmarket.ir',  # زیردامنه www
    '192.168.1.157',      # IP داخلی سرور
    'localhost',          # برای تست محلی
    '127.0.0.1',          # برای تست محلی
    '0.0.0.0',            # برای همه IPها
    '.plasmarket.ir',     # همه زیردامنه‌ها
    '*',                  # ⚠️ موقتاً برای تست - در تولید حذف شود
]
CSRF_TRUSTED_ORIGINS = [
    "https://plasmarket.ir",
    "https://www.plasmarket.ir",
    "http://plasmarket.ir",
    "http://www.plasmarket.ir",
    "http://192.168.1.157",
    "https://192.168.1.157",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

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
SESSION_ENGINE = 'django.contrib.sessions.backends.db'  # یا 'django.contrib.sessions.backends.cache'
SESSION_COOKIE_AGE = 1209600  # 2 هفته (پیش‌فرض)
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
ROOT_URLCONF = 'plasco.urls'


# SESSION_ENGINE = 'django.contrib.sessions.backends.db'  # حتماً از دیتابیس استفاده کنید
# SESSION_COOKIE_NAME = 'plasco_session_id'
# SESSION_COOKIE_AGE = 3600 * 24  # 24 ساعت
# SESSION_EXPIRE_AT_BROWSER_CLOSE = True
# SESSION_COOKIE_SECURE = True  # برای HTTPS
# SESSION_COOKIE_HTTPONLY = True
# SESSION_COOKIE_SAMESITE = 'Lax'
# SESSION_SAVE_EVERY_REQUEST = True

# جلوگیری از cache شدن صفحات حساس
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-plasco-cache',
    }
}

# Middlewareها باید به این ترتیب باشند
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',  # این خط مهم
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',  # این خط مهم
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    # 'plasco.middleware.StrictSessionMiddleware',  # این خط را اضافه کنید
    # 'cantact_app.middleware.SingleSessionMiddleware',
]

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

# ------------------------------------------------اوکال و محلی---------------------------------------------
#
# from pathlib import Path
# import os
#
# import locale
# import sys
# import io
#
# # Fix Unicode encoding in Windows terminal
# if sys.platform == "win32":
#     sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
#     sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
#
# # Build paths inside the project like this: BASE_DIR / 'subdir'.
# BASE_DIR = Path(__file__).resolve().parent.parent
#
#
# # Quick-start development settings - unsuitable for production
# # See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/
#
# # SECURITY WARNING: keep the secret key used in production secret!
# SECRET_KEY = 'django-insecure-9a=faq-)zl&%@!5(9t8!0r(ar)&()3l+hc#a)+-!eh$-ljkdh@'
#
# # SECURITY WARNING: don't run with debug turned on in production!
# DEBUG = True
# # ALLOWED_HOSTS = ['http://plasmarket.ir','plasmarket.ir','www.plasmarket.ir','https://plasmarket.ir','192.168.1.157']
# # CSRF_TRUSTED_ORIGINS = ["https://plasmarket.ir",'http://plasmarket.ir','https://www.plasmarket.ir','http://www.plasmarket.ir']
#
# ALLOWED_HOSTS = []
#
#
# # Application definition
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
#
#
# JALALI_DATE_DEFAULTS = {
#    'Strftime': {
#         'date': '%y/%m/%d',
#         'datetime': '%H:%M:%S _ %y%m%d',
#     },
#     'Static':{
#         'js':[
#             # loading datepicker
#             'admin/js/django_jalali.min.js',
#             # OR
#             # 'admin/jquery.ui.datepicker.jalali/scripts/jquery.ui.core.js',
#             # 'admin/jquery.ui.datepicker.jalali/scripts/calender.js',
#             # 'admin/jquery.ui.datepicker.jalali/scripts/jquery.ui.datepicker-cc.js',
#             # 'admin/jquery.ui.datepicker.jalali/scripts/jquery.ui.datepicker-cc-fa.js',
#             # 'admin/js/main.js',
#         ],
#         'css': {
#             'all': [
#                 'admin/jquery.ui.datepicker.jalali/themes/base/jquery-ui.min.css',
#             ]
#         }
#     },
# }
#
# MIDDLEWARE = [
#     'django.middleware.security.SecurityMiddleware',
#     'django.contrib.sessions.middleware.SessionMiddleware',
#     'django.middleware.common.CommonMiddleware',
#     'django.middleware.csrf.CsrfViewMiddleware',
#     'django.contrib.auth.middleware.AuthenticationMiddleware',
#     'django.contrib.messages.middleware.MessageMiddleware',
#     'django.middleware.clickjacking.XFrameOptionsMiddleware',
# ]
#
# ROOT_URLCONF = 'plasco.urls'
#
# TEMPLATES = [
#     {
#         'BACKEND': 'django.template.backends.django.DjangoTemplates',
#         'DIRS': [BASE_DIR / 'templates']
#         ,
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
#
# # Database
# # https://docs.djangoproject.com/en/5.2/ref/settings/#databases
#
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }
#
#
#
#
#
# # DATABASES = {
# #     'default': {
# #         'ENGINE': 'django.db.backends.mysql',
# #         'NAME': 'plascodavor_db',
# #         'USER': 'root',
# #         'PASSWORD': 'zh21oYmLXiINj!Es3Rtq',
# #         'HOST': 'plascodata1-ayh-service',
# #
# #     }
# # }
#
#
# # Password validation
# # https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators
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
#
# # Internationalization
# # https://docs.djangoproject.com/en/5.2/topics/i18n/
#
# LANGUAGE_CODE = 'fa-ir'
#
# TIME_ZONE = 'UTC'
#
# USE_I18N = True
#
# USE_TZ = True
#
#
# # Static files (CSS, JavaScript, Images)
# # https://docs.djangoproject.com/en/5.2/howto/static-files/
#
# STATIC_URL = '/static/'
# MEDIA_URL = '/media/'
# STATICFILES_DIRS=[os.path.join(BASE_DIR,'static')]
# STATIC_ROOT='/static/'
# MEDIA_ROOT = os.path.join(BASE_DIR,'media')
#
#
# # Default primary key field type
# # https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field
#
# DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
#
#
#
# AZ_IRANIAN_BANK_GATEWAYS = {
#    'GATEWAYS': {
#        # 'BMI': {
#        #     'MERCHANT_CODE': '<YOUR MERCHANT CODE>',
#        #     'TERMINAL_CODE': '<YOUR TERMINAL CODE>',
#        #     'SECRET_KEY': '<YOUR SECRET CODE>',
#        # },
#        # 'SEP': {
#        #     'MERCHANT_CODE': '<YOUR MERCHANT CODE>',
#        #     'TERMINAL_CODE': '<YOUR TERMINAL CODE>',
#        # },
#        # 'ZARINPAL': {
#        #     'MERCHANT_CODE': '<YOUR MERCHANT CODE>',
#        #     'SANDBOX': 0,  # 0 disable, 1 active
#        # },
#        'IDPAY': {
#            'MERCHANT_CODE': '021de8d3-3eb3-40ba-b0e3-01883a6575e1',
#            'METHOD': 'POST',  # GET or POST
#            'X_SANDBOX': 1,  # 0 disable, 1 active
#        },
#        # 'ZIBAL': {
#        #     'MERCHANT_CODE': '64c2047fcbbc270017f4c6b2',
#        # },
#        # 'BAHAMTA': {
#        #     'MERCHANT_CODE': '<YOUR MERCHANT CODE>',
#        # },
#        # 'MELLAT': {
#        #     'TERMINAL_CODE': '<YOUR TERMINAL CODE>',
#        #     'USERNAME': '<YOUR USERNAME>',
#        #     'PASSWORD': '<YOUR PASSWORD>',
#        # },
#        # 'PAYV1': {
#        #     'MERCHANT_CODE': '<YOUR MERCHANT CODE>',
#        #     'X_SANDBOX': 0,  # 0 disable, 1 active
#        # },
#    },
#    # 'IS_SAMPLE_FORM_ENABLE': True, # اختیاری و پیش فرض غیر فعال است
#    'DEFAULT': 'IDPAY',
#    'CURRENCY': 'IRR', # اختیاری
#    'TRACKING_CODE_QUERY_PARAM': 'tc', # اختیاری
#    'TRACKING_CODE_LENGTH': 16, # اختیاری
#    'SETTING_VALUE_READER_CLASS': 'azbankgateways.readers.DefaultReader', # اختیاری
#    'BANK_PRIORITIES': [
#        # 'BMI',
#        # 'SEP',
#        # and so on ...
#    ], # اختیاری
#     # 'IS_SAMPLE_FORM_ENABLE': True,
#    'IS_SAFE_GET_GATEWAY_PAYMENT': True, #اختیاری، بهتر است True بزارید.
#    # 'CUSTOM_APP': None, # اختیاری
# }
#
# MERCHANT = '021de8d3-3eb3-40ba-b0e3-01883a6575e1'
# SANDBOX = True
# # LOGGING = {
# #     'version': 1,
# #     'disable_existing_loggers': False,
# #     'handlers': {
# #         'console': {
# #             'class': 'logging.StreamHandler',
# #         },
# #     },
# #     'root': {
# #         'handlers': ['console'],
# #         'level': 'DEBUG',
# #     },
# # }
#
