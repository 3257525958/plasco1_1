from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from plasco.offline_ip_manager import is_allowed_offline_ip, get_client_ip


def control_panel(request):
    """صفحه کنترل پنل برای انتخاب حالت اجرا"""
    if not is_allowed_offline_ip(request):
        # اگر IP مجاز نبود، مستقیماً به حالت آنلاین هدایت شود
        request.session['operation_mode'] = 'online'
        return redirect('/')  # به صفحه اصلی هدایت شود

    context = {
        'client_ip': get_client_ip(request),
    }
    return render(request, 'control_panel/control_panel.html', context)


@csrf_exempt
def set_mode(request):
    """تنظیم حالت اجرای سیستم"""
    if request.method == 'POST':
        mode = request.POST.get('mode')
        client_ip = get_client_ip(request)

        if mode == 'online':
            # اجرا در حالت آنلاین
            request.session['operation_mode'] = 'online'
            return JsonResponse({
                'status': 'success',
                'message': 'حالت آنلاین فعال شد',
                'redirect': '/'  # به صفحه اصلی (home_def) هدایت شود
            })

        elif mode == 'offline':
            # اجرا در حالت آفلاین
            request.session['operation_mode'] = 'offline'
            return JsonResponse({
                'status': 'success',
                'message': 'در حال بررسی و نصب حالت آفلاین...',
                'redirect': '/offline/install/'
            })

    return JsonResponse({'status': 'error', 'message': 'درخواست نامعتبر'})