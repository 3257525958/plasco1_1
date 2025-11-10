from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import AllowedIP
import json


def manage_ips(request):
    """صفحه مدیریت IPها"""
    return render(request, 'ip_manager/manage_ips.html')


@csrf_exempt
def list_ips(request):
    """دریافت لیست IPها (API)"""
    ips = AllowedIP.objects.all().order_by('-created_at')
    ip_list = []

    for ip in ips:
        ip_list.append({
            'id': ip.id,
            'ip_address': ip.ip_address,
            'description': ip.description,
            'is_active': ip.is_active,
            'created_at': ip.created_at.strftime('%Y/%m/%d %H:%M')
        })

    return JsonResponse({'status': 'success', 'ips': ip_list})


@csrf_exempt
def add_ip(request):
    """افزودن IP جدید (API)"""
    if request.method == 'POST':
        ip_address = request.POST.get('ip_address')
        description = request.POST.get('description', '')

        if AllowedIP.objects.filter(ip_address=ip_address).exists():
            return JsonResponse({'status': 'error', 'message': 'این IP قبلاً ثبت شده است'})

        AllowedIP.objects.create(
            ip_address=ip_address,
            description=description
        )
        return JsonResponse({'status': 'success'})


@csrf_exempt
def delete_ip(request, ip_id):
    """حذف IP (API)"""
    ip = get_object_or_404(AllowedIP, id=ip_id)
    ip.delete()
    return JsonResponse({'status': 'success'})


@csrf_exempt
def update_ip(request, ip_id):
    """ویرایش IP (API)"""
    ip = get_object_or_404(AllowedIP, id=ip_id)
    ip.ip_address = request.POST.get('ip_address')
    ip.description = request.POST.get('description', '')
    ip.save()
    return JsonResponse({'status': 'success'})


@csrf_exempt
def toggle_ip(request, ip_id):
    """فعال/غیرفعال کردن IP (API)"""
    ip = get_object_or_404(AllowedIP, id=ip_id)
    action = request.POST.get('action')

    if action == 'activate':
        ip.is_active = True
    elif action == 'deactivate':
        ip.is_active = False

    ip.save()
    return JsonResponse({'status': 'success'})