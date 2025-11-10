"""
مدیریت IPهای مجاز برای سیستم آفلاین
نسخه کامل با پشتیبانی از دیتابیس و fallback به لیست ثابت
"""

from pathlib import Path
import os

# لیست IPهای مجاز برای حالت آفلاین (fallback)
ALLOWED_OFFLINE_IPS = [
    '192.168.1.172',
    '192.168.1.157',
    '192.168.1.100',
    '192.168.1.101',
    '192.168.1.142',
    '127.0.0.1',
    'localhost',
    '5.114.242.203',
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
    """بررسی آیا IP کاربر مجاز است"""
    client_ip = get_client_ip(request)

    # بررسی IPهای خاص
    if client_ip in ['127.0.0.1', 'localhost']:
        return True

    # اول سعی کن از دیتابیس بخونی
    try:
        from ip_manager.models import AllowedIP
        return AllowedIP.objects.filter(
            ip_address=client_ip,
            is_active=True
        ).exists()
    except Exception as e:
        # اگر دیتابیس مشکل داشت، از لیست ثابت استفاده کن
        print(f"⚠️ خطا در دسترسی به دیتابیس: {e} - استفاده از لیست ثابت")
        return client_ip in ALLOWED_OFFLINE_IPS

def add_allowed_ip(ip_address, description=""):
    """افزودن IP جدید به دیتابیس"""
    try:
        from ip_manager.models import AllowedIP
        ip, created = AllowedIP.objects.get_or_create(
            ip_address=ip_address,
            defaults={'description': description}
        )
        if created:
            print(f"✅ IP {ip_address} به دیتابیس اضافه شد")
        return created
    except Exception as e:
        print(f"⚠️ خطا در افزودن IP به دیتابیس: {e}")
        # fallback به لیست ثابت
        if ip_address not in ALLOWED_OFFLINE_IPS:
            ALLOWED_OFFLINE_IPS.append(ip_address)
            print(f"✅ IP {ip_address} به لیست ثابت اضافه شد")
            return True
        return False

def remove_allowed_ip(ip_address):
    """حذف IP از دیتابیس"""
    try:
        from ip_manager.models import AllowedIP
        deleted, _ = AllowedIP.objects.filter(ip_address=ip_address).delete()
        if deleted > 0:
            print(f"✅ IP {ip_address} از دیتابیس حذف شد")
        return deleted > 0
    except Exception as e:
        print(f"⚠️ خطا در حذف IP از دیتابیس: {e}")
        # fallback به لیست ثابت
        if ip_address in ALLOWED_OFFLINE_IPS:
            ALLOWED_OFFLINE_IPS.remove(ip_address)
            print(f"✅ IP {ip_address} از لیست ثابت حذف شد")
            return True
        return False

def update_allowed_ip(ip_id, ip_address, description=""):
    """ویرایش IP در دیتابیس"""
    try:
        from ip_manager.models import AllowedIP
        ip = AllowedIP.objects.get(id=ip_id)
        ip.ip_address = ip_address
        ip.description = description
        ip.save()
        print(f"✅ IP {ip_address} ویرایش شد")
        return True
    except Exception as e:
        print(f"⚠️ خطا در ویرایش IP: {e}")
        return False

def toggle_allowed_ip(ip_id, is_active):
    """فعال/غیرفعال کردن IP"""
    try:
        from ip_manager.models import AllowedIP
        ip = AllowedIP.objects.get(id=ip_id)
        ip.is_active = is_active
        ip.save()
        status = "فعال" if is_active else "غیرفعال"
        print(f"✅ IP {ip.ip_address} {status} شد")
        return True
    except Exception as e:
        print(f"⚠️ خطا در تغییر وضعیت IP: {e}")
        return False

def get_all_allowed_ips():
    """دریافت همه IPهای مجاز"""
    try:
        from ip_manager.models import AllowedIP
        ips = list(AllowedIP.objects.filter(is_active=True).values_list('ip_address', flat=True))
        print(f"✅ {len(ips)} IP از دیتابیس دریافت شد")
        return ips
    except Exception as e:
        print(f"⚠️ خطا در دریافت IPها از دیتابیس: {e}")
        print(f"✅ استفاده از {len(ALLOWED_OFFLINE_IPS)} IP از لیست ثابت")
        return ALLOWED_OFFLINE_IPS

def get_allowed_ips_with_details():
    """دریافت همه IPهای مجاز با جزئیات"""
    try:
        from ip_manager.models import AllowedIP
        ips = AllowedIP.objects.all().order_by('-created_at')
        return ips
    except Exception as e:
        print(f"⚠️ خطا در دریافت جزئیات IPها: {e}")
        # ساخت لیست ساده از لیست ثابت
        simple_ips = []
        for ip in ALLOWED_OFFLINE_IPS:
            simple_ips.append({
                'ip_address': ip,
                'description': 'از لیست ثابت',
                'is_active': True
            })
        return simple_ips

def initialize_default_ips():
    """مقداردهی اولیه IPهای پیش‌فرض در دیتابیس"""
    try:
        from ip_manager.models import AllowedIP

        default_ips = [
            {'ip': '192.168.1.172', 'desc': 'کامپیوتر مدیر سیستم'},
            {'ip': '192.168.1.157', 'desc': 'کامپیوتر اتاق سرور'},
            {'ip': '192.168.1.100', 'desc': 'کامپیوتر مالی ۱'},
            {'ip': '192.168.1.101', 'desc': 'کامپیوتر مالی ۲'},
        ]

        created_count = 0
        for ip_data in default_ips:
            ip, created = AllowedIP.objects.get_or_create(
                ip_address=ip_data['ip'],
                defaults={'description': ip_data['desc']}
            )
            if created:
                created_count += 1

        print(f"✅ {created_count} IP پیش‌فرض در دیتابیس ایجاد شد")
        return created_count

    except Exception as e:
        print(f"⚠️ خطا در مقداردهی اولیه IPها: {e}")
        return 0

# وقتی ماژول import میشه، IPهای پیش‌فرض رو بررسی کن
try:
    from ip_manager.models import AllowedIP
    if not AllowedIP.objects.exists():
        print("🔧 در حال مقداردهی اولیه IPهای پیش‌فرض...")
        initialize_default_ips()
except Exception as e:
    print(f"⚠️ خطا در بررسی IPهای پیش‌فرض: {e}")