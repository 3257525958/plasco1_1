import os
from pathlib import Path

# لیست IPهای مجاز برای حالت آفلاین
# لیست IPهای مجاز برای حالت آفلاین
ALLOWED_OFFLINE_IPS = [
    '192.168.1.172',
    '192.168.1.157',
    '192.168.1.100',
    '192.168.1.101',
    '127.0.0.1',
    'localhost',
    '10.206.217.99',    # IP قبلی شما
    '5.114.242.203',    # IP جدید شما - این خط را اضافه کنید
    '10.206.217.*'      # کل range شبکه شما
    '192.168.1.142'
]



def get_client_ip(request):
    """دریافت IP واقعی کاربر"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def is_allowed_offline_ip(request):
    """بررسی آیا IP کاربر جزو لیست مجاز است"""
    client_ip = get_client_ip(request)

    # بررسی localhost و IPهای خاص
    if client_ip in ['127.0.0.1', 'localhost']:
        return True

    # بررسی IPهای مجاز
    return client_ip in ALLOWED_OFFLINE_IPS


def add_allowed_ip(ip_address):
    """افزودن IP جدید به لیست مجاز"""
    if ip_address not in ALLOWED_OFFLINE_IPS:
        ALLOWED_OFFLINE_IPS.append(ip_address)
        return True
    return False


def get_allowed_ips():
    """دریافت لیست IPهای مجاز"""
    return ALLOWED_OFFLINE_IPS