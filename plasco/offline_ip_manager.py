from ip_manager.models import AllowedIP


def is_allowed_offline_ip(request):
    """بررسی آیا IP کاربر از دیتابیس مجاز است"""
    client_ip = get_client_ip(request)

    # بررسی IPهای خاص
    if client_ip in ['127.0.0.1', 'localhost']:
        return True

    # بررسی از دیتابیس
    try:
        return AllowedIP.objects.filter(
            ip_address=client_ip,
            is_active=True
        ).exists()
    except:
        # اگر دیتابیس مشکل داشت، از لیست ثابت استفاده کن
        return client_ip in ALLOWED_OFFLINE_IPS


def add_allowed_ip(ip_address, description=""):
    """افزودن IP جدید به دیتابیس"""
    try:
        ip, created = AllowedIP.objects.get_or_create(
            ip_address=ip_address,
            defaults={'description': description}
        )
        return created
    except:
        return False


def remove_allowed_ip(ip_address):
    """حذف IP از دیتابیس"""
    try:
        deleted, _ = AllowedIP.objects.filter(ip_address=ip_address).delete()
        return deleted > 0
    except:
        return False


def get_all_allowed_ips():
    """دریافت همه IPهای مجاز"""
    try:
        return list(AllowedIP.objects.filter(is_active=True).values_list('ip_address', flat=True))
    except:
        return ALLOWED_OFFLINE_IPS