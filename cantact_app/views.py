# در فایل views.py، بخش مدیریت سشن را اینگونه اصلاح کنید:

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from cantact_app.models import UserSessionLog

# 🔥 تغییر مهم: اضافه کردن login_url به دکوراتورها
@login_required(login_url='/cantact/login/')
def session_management_view(request):
    """صفحه مدیریت سشن‌های کاربر"""
    user_sessions = UserSessionLog.get_user_sessions(request.user)
    current_session_key = request.session.session_key

    context = {
        'user_sessions': user_sessions,
        'current_session_key': current_session_key,
        'max_sessions': 1,
    }

    return render(request, 'cantact_app/session_management.html', context)

@login_required(login_url='/cantact/login/')
def terminate_other_sessions_view(request):
    """خاتمه دادن به سایر سشن‌های کاربر"""
    if request.method == 'POST':
        current_session_key = request.session.session_key

        # خاتمه تمام سشن‌های دیگر
        other_sessions = UserSessionLog.objects.filter(
            user=request.user,
            is_active=True
        ).exclude(session_key=current_session_key)

        terminated_count = 0
        for session_log in other_sessions:
            session_log.terminate()
            terminated_count += 1

        messages.success(request, f"✅ {terminated_count} سشن دیگر خاتمه یافت.")

    return redirect('cantact_app:session_management')