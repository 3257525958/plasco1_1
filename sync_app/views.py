from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import subprocess
import threading
import json
import os
from .models import DataSyncLog




@csrf_exempt
def execute_command(request):
    """اجرای دستورات مدیریتی"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            command = data.get('command')

            if not command:
                return JsonResponse({'status': 'error', 'message': 'دستور مشخص نشده'})

            # لیست دستورات مجاز
            allowed_commands = [
                'sync_full_cantact', 'sync_full_account', 'sync_full_dashbord',
                'sync_full_invoice', 'sync_full_pos_payment', 'clear_all_sync_logs',
                'sync_status', 'start_sync_service', 'stop_sync_service', 'sync_now',
                'clean_sync_logs', 'makemigrations', 'migrate'
            ]

            if command not in allowed_commands:
                return JsonResponse({'status': 'error', 'message': 'دستور غیرمجاز'})

            # اضافه کردن آرگومان‌ها
            full_command = ['python', 'manage.py', command]

            if command == 'clean_sync_logs':
                full_command.extend(['--days', '30'])

            # اجرای دستور در thread جداگانه
            def run_command():
                try:
                    result = subprocess.run(
                        full_command,
                        capture_output=True,
                        text=True,
                        timeout=300,  # 5 دقیقه timeout
                        cwd=settings.BASE_DIR
                    )

                    # ذخیره نتیجه در فایل
                    with open(os.path.join(settings.BASE_DIR, 'sync_log.txt'), 'w', encoding='utf-8') as f:
                        f.write(f"STDOUT:\n{result.stdout}\n")
                        f.write(f"STDERR:\n{result.stderr}\n")
                        f.write(f"RETURN CODE: {result.returncode}\n")

                except subprocess.TimeoutExpired:
                    with open(os.path.join(settings.BASE_DIR, 'sync_log.txt'), 'w', encoding='utf-8') as f:
                        f.write("❌ دستور به دلیل timeout متوقف شد\n")
                except Exception as e:
                    with open(os.path.join(settings.BASE_DIR, 'sync_log.txt'), 'w', encoding='utf-8') as f:
                        f.write(f"❌ خطا در اجرای دستور: {str(e)}\n")

            # اجرای غیرهمزمان
            thread = threading.Thread(target=run_command)
            thread.daemon = True
            thread.start()

            return JsonResponse({
                'status': 'success',
                'message': f'دستور {command} در حال اجراست...'
            })

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'error', 'message': 'متد غیرمجاز'})


def get_command_status(request):
    """دریافت وضعیت اجرای دستور"""
    try:
        log_file = os.path.join(settings.BASE_DIR, 'sync_log.txt')
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
            return JsonResponse({'status': 'success', 'content': content})
        else:
            return JsonResponse({'status': 'success', 'content': 'هنوز دستوری اجرا نشده است.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


def get_sync_stats(request):
    """دریافت آمار سینک"""
    try:
        total_logs = DataSyncLog.objects.count()
        synced_logs = DataSyncLog.objects.filter(sync_status=True).count()
        unsynced_logs = DataSyncLog.objects.filter(sync_status=False).count()

        return JsonResponse({
            'status': 'success',
            'stats': {
                'total_logs': total_logs,
                'synced_logs': synced_logs,
                'unsynced_logs': unsynced_logs
            }
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


import requests
from django.conf import settings

def get_connection_status(request):
    """بررسی وضعیت اتصال به سرور"""
    try:
        response = requests.get(
            f"{settings.ONLINE_SERVER_URL}/",
            timeout=10,
            verify=False
        )
        return JsonResponse({
            'status': 'success',
            'connected': True,
            'server_url': settings.ONLINE_SERVER_URL,
            'message': 'اتصال به سرور برقرار است'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'success',
            'connected': False,
            'server_url': settings.ONLINE_SERVER_URL,
            'message': f'خطا در اتصال: {str(e)}'
        })


from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import subprocess
import threading
import json
import os
import socket
import requests
from .models import DataSyncLog
import time

# --------------------------------------------------------------------------------------------------------
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import subprocess
import threading
import json
import os
import socket
import requests
from .models import DataSyncLog
import time
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required


@staff_member_required
def sync_control_panel(request):
    """پنل کنترل سینک - نسخه بهبود یافته"""
    return render(request, 'sync_app/control_panel.html')


@csrf_exempt
def execute_command(request):
    """اجرای دستورات مدیریتی - نسخه بهبود یافته"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            command = data.get('command')

            if not command:
                return JsonResponse({'status': 'error', 'message': 'دستور مشخص نشده'})

            # دستورات مجاز جدید
            allowed_commands = [
                'sync_full_cantact', 'sync_full_account', 'sync_full_dashbord',
                'sync_full_invoice', 'sync_full_pos_payment', 'clear_all_sync_logs',
                'sync_status', 'start_sync_service', 'stop_sync_service', 'sync_now',
                'clean_sync_logs', 'makemigrations', 'migrate',
                'full_data_transfer',  # دستور جدید برای انتقال کامل
                'clear_local_db'  # دستور جدید برای پاکسازی دیتابیس
            ]

            if command not in allowed_commands:
                return JsonResponse({'status': 'error', 'message': 'دستور غیرمجاز'})

            # اجرای دستور در thread جداگانه
            if command == 'full_data_transfer':
                thread = threading.Thread(target=full_data_transfer_process, daemon=True)
                thread.start()
                return JsonResponse({
                    'status': 'success',
                    'message': 'فرآیند انتقال کامل داده‌ها شروع شد...'
                })
            elif command == 'clear_local_db':
                thread = threading.Thread(target=clear_local_db_process, daemon=True)
                thread.start()
                return JsonResponse({
                    'status': 'success',
                    'message': 'فرآیند پاکسازی دیتابیس لوکال شروع شد...'
                })
            else:
                # اجرای دستورات عادی
                full_command = ['python', 'manage.py', command]
                if command == 'clean_sync_logs':
                    full_command.extend(['--days', '30'])

                thread = threading.Thread(target=run_command, args=(full_command,), daemon=True)
                thread.start()
                return JsonResponse({
                    'status': 'success',
                    'message': f'دستور {command} در حال اجراست...'
                })

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'error', 'message': 'متد غیرمجاز'})


def run_command(full_command):
    """اجرای دستور در background"""
    try:
        result = subprocess.run(
            full_command,
            capture_output=True,
            text=True,
            timeout=300,
            cwd=settings.BASE_DIR
        )

        # ذخیره نتیجه در فایل
        with open(os.path.join(settings.BASE_DIR, 'sync_log.txt'), 'w', encoding='utf-8') as f:
            f.write(f"STDOUT:\n{result.stdout}\n")
            f.write(f"STDERR:\n{result.stderr}\n")
            f.write(f"RETURN CODE: {result.returncode}\n")

    except subprocess.TimeoutExpired:
        with open(os.path.join(settings.BASE_DIR, 'sync_log.txt'), 'w', encoding='utf-8') as f:
            f.write("❌ دستور به دلیل timeout متوقف شد\n")
    except Exception as e:
        with open(os.path.join(settings.BASE_DIR, 'sync_log.txt'), 'w', encoding='utf-8') as f:
            f.write(f"❌ خطا در اجرای دستور: {str(e)}\n")


def full_data_transfer_process():
    """فرآیند کامل انتقال داده به کامپیوتر محلی"""
    try:
        progress_file = os.path.join(settings.BASE_DIR, 'transfer_progress.json')

        # مرحله 0: پاکسازی دیتابیس لوکال
        update_progress(progress_file, 0, "🧹 در حال پاکسازی دیتابیس لوکال...")
        run_command_sync(['python', 'manage.py', 'clear_local_db', '--force'])

        # مرحله 1: انتقال cantact_app
        update_progress(progress_file, 10, "📞 در حال انتقال اطلاعات مخاطبان...")
        run_command_sync(['python', 'manage.py', 'sync_full_cantact'])

        # مرحله 2: انتقال account_app
        update_progress(progress_file, 30, "💰 در حال انتقال اطلاعات مالی...")
        run_command_sync(['python', 'manage.py', 'sync_full_account'])

        # مرحله 3: انتقال dashbord_app
        update_progress(progress_file, 50, "📊 در حال انتقال اطلاعات داشبورد...")
        run_command_sync(['python', 'manage.py', 'sync_full_dashbord'])

        # مرحله 4: انتقال pos_payment
        update_progress(progress_file, 70, "💳 در حال انتقال اطلاعات تراکنش‌ها...")
        run_command_sync(['python', 'manage.py', 'sync_full_pos_payment'])

        # مرحله 5: انتقال invoice_app
        update_progress(progress_file, 85, "🧾 در حال انتقال اطلاعات فاکتورها...")
        run_command_sync(['python', 'manage.py', 'sync_full_invoice'])

        # مرحله 6: ایجاد سوپریوزر
        update_progress(progress_file, 90, "👑 در حال ایجاد کاربر مدیر...")
        superuser_info = create_local_superuser()

        # مرحله 7: پاکسازی لاگ‌ها
        update_progress(progress_file, 95, "🧹 در حال پاکسازی لاگ‌های سینک...")
        run_command_sync(['python', 'manage.py', 'clear_all_sync_logs', '--force'])

        # مرحله 8: تکمیل فرآیند
        update_progress(progress_file, 100, "✅ انتقال داده‌ها با موفقیت انجام شد!", {
            'completed': True,
            'superuser_info': superuser_info
        })

    except Exception as e:
        update_progress(progress_file, 0, f"❌ خطا در انتقال داده‌ها: {str(e)}", {'error': True})


def clear_local_db_process():
    """فرآیند پاکسازی دیتابیس لوکال"""
    try:
        progress_file = os.path.join(settings.BASE_DIR, 'transfer_progress.json')
        update_progress(progress_file, 0, "🧹 در حال پاکسازی دیتابیس لوکال...")
        run_command_sync(['python', 'manage.py', 'clear_local_db', '--force'])
        update_progress(progress_file, 100, "✅ پاکسازی دیتابیس با موفقیت انجام شد!", {'completed': True})
    except Exception as e:
        update_progress(progress_file, 0, f"❌ خطا در پاکسازی: {str(e)}", {'error': True})


def run_command_sync(full_command):
    """اجرای همزمان دستور و بازگشت نتیجه"""
    try:
        result = subprocess.run(
            full_command,
            capture_output=True,
            text=True,
            timeout=300,
            cwd=settings.BASE_DIR,
            encoding='utf-8'
        )

        # ذخیره نتیجه
        with open(os.path.join(settings.BASE_DIR, 'sync_log.txt'), 'a', encoding='utf-8') as f:
            f.write(f"\n\n=== دستور: {' '.join(full_command)} ===\n")
            f.write(f"STDOUT:\n{result.stdout}\n")
            if result.stderr:
                f.write(f"STDERR:\n{result.stderr}\n")
            f.write(f"RETURN CODE: {result.returncode}\n")

        return result.returncode == 0

    except subprocess.TimeoutExpired:
        with open(os.path.join(settings.BASE_DIR, 'sync_log.txt'), 'a', encoding='utf-8') as f:
            f.write(f"❌ دستور به دلیل timeout متوقف شد: {' '.join(full_command)}\n")
        return False
    except Exception as e:
        with open(os.path.join(settings.BASE_DIR, 'sync_log.txt'), 'a', encoding='utf-8') as f:
            f.write(f"❌ خطا در اجرای دستور: {str(e)}\n")
        return False


def create_local_superuser():
    """ایجاد سوپریوزر با نام کاربری و رمز برابر IP کامپیوتر"""
    try:
        # دریافت IP کامپیوتر
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)

        username = local_ip
        password = local_ip

        # ایجاد سوپریوزر
        from django.contrib.auth.models import User

        # حذف کاربر قبلی اگر وجود دارد
        User.objects.filter(username=username).delete()

        # ایجاد کاربر جدید
        user = User.objects.create_superuser(
            username=username,
            email=f'{username}@local.plasco',
            password=password
        )

        return {
            'username': username,
            'password': password,
            'hostname': hostname,
            'message': f'کاربر مدیر با موفقیت ایجاد شد. از اطلاعات زیر برای ورود استفاده کنید:'
        }

    except Exception as e:
        return {
            'username': 'admin',
            'password': 'admin',
            'hostname': 'localhost',
            'message': f'خطا در ایجاد کاربر: {str(e)}. از کاربر پیش‌فرض استفاده کنید.'
        }


def update_progress(progress_file, percentage, message, extra_data=None):
    """بروزرسانی فایل پیشرفت"""
    progress_data = {
        'percentage': percentage,
        'message': message,
        'timestamp': time.time()
    }

    if extra_data:
        progress_data.update(extra_data)

    try:
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, ensure_ascii=False)
    except Exception as e:
        print(f"خطا در ذخیره پیشرفت: {e}")


def get_transfer_progress(request):
    """دریافت وضعیت پیشرفت انتقال داده‌ها"""
    try:
        progress_file = os.path.join(settings.BASE_DIR, 'transfer_progress.json')
        if os.path.exists(progress_file):
            with open(progress_file, 'r', encoding='utf-8') as f:
                progress_data = json.load(f)
            return JsonResponse({'status': 'success', 'data': progress_data})
        else:
            return JsonResponse({'status': 'success', 'data': {
                'percentage': 0,
                'message': 'آماده برای شروع...',
                'completed': False
            }})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


def get_command_status(request):
    """دریافت وضعیت اجرای دستور"""
    try:
        log_file = os.path.join(settings.BASE_DIR, 'sync_log.txt')
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
            return JsonResponse({'status': 'success', 'content': content})
        else:
            return JsonResponse({'status': 'success', 'content': 'هنوز دستوری اجرا نشده است.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


@csrf_exempt
def execute_command(request):
    """اجرای دستورات مدیریتی - نسخه بهبود یافته"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            command = data.get('command')

            if not command:
                return JsonResponse({'status': 'error', 'message': 'دستور مشخص نشده'})

            # دستورات مجاز جدید
            allowed_commands = [
                'sync_full_cantact', 'sync_full_account', 'sync_full_dashbord',
                'sync_full_invoice', 'sync_full_pos_payment', 'clear_all_sync_logs',
                'sync_status', 'start_sync_service', 'stop_sync_service', 'sync_now',
                'clean_sync_logs', 'makemigrations', 'migrate',
                'full_data_transfer',  # دستور جدید برای انتقال کامل
                'clear_local_db'  # دستور جدید برای پاکسازی دیتابیس
            ]

            if command not in allowed_commands:
                return JsonResponse({'status': 'error', 'message': 'دستور غیرمجاز'})

            # اجرای دستور در thread جداگانه
            if command == 'full_data_transfer':
                thread = threading.Thread(target=full_data_transfer_process, daemon=True)
                thread.start()
                return JsonResponse({
                    'status': 'success',
                    'message': 'فرآیند انتقال کامل داده‌ها شروع شد...'
                })
            elif command == 'clear_local_db':
                thread = threading.Thread(target=clear_local_db_process, daemon=True)
                thread.start()
                return JsonResponse({
                    'status': 'success',
                    'message': 'فرآیند پاکسازی دیتابیس لوکال شروع شد...'
                })
            else:
                # اجرای دستورات عادی
                full_command = ['python', 'manage.py', command]
                if command == 'clean_sync_logs':
                    full_command.extend(['--days', '30'])

                thread = threading.Thread(target=run_command, args=(full_command,), daemon=True)
                thread.start()
                return JsonResponse({
                    'status': 'success',
                    'message': f'دستور {command} در حال اجراست...'
                })

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'error', 'message': 'متد غیرمجاز'})


