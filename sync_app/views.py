from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import subprocess
import threading
import json
import os
from .models import DataSyncLog


def sync_control_panel(request):
    """پنل کنترل سینک"""
    return render(request, 'sync_app/control_panel.html')


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