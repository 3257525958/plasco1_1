from django.db import models
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.apps import apps
from django.utils import timezone
from .models import ChangeTracker
import decimal


# در sync_api/views.py
@api_view(['GET'])
def sync_pull(request):
    """ارسال تغییرات از سرور به لوکال - بهینه‌سازی شده"""
    try:
        last_sync_str = request.GET.get('last_sync')
        last_sync = timezone.datetime.fromisoformat(last_sync_str) if last_sync_str else None

        print(f"📤 ارسال تغییرات از سرور - آخرین سینک: {last_sync}")

        # پیدا کردن تغییرات جدید با محدودیت
        if last_sync:
            changes_tracked = ChangeTracker.objects.filter(
                created_at__gt=last_sync,
                sync_status=False
            )[:100]  # محدود به 100 رکورد
        else:
            changes_tracked = ChangeTracker.objects.filter(sync_status=False)[:100]  # محدود به 100 رکورد

        changes = []
        for tracker in changes_tracked:
            try:
                # پردازش ساده‌تر
                changes.append({
                    'app_name': tracker.app_name,
                    'model_type': tracker.model_name,
                    'record_id': tracker.record_id,
                    'action': tracker.action,
                    'data': tracker.data or {},
                    'tracker_id': tracker.id,
                    'changed_at': tracker.created_at.isoformat()
                })
            except Exception as e:
                print(f"⚠️ خطا در پردازش تغییرات {tracker}: {e}")
                continue

        print(f"🎯 ارسال {len(changes)} تغییر از سرور")

        return Response({
            'status': 'success',
            'message': f'ارسال {len(changes)} تغییر از سرور',
            'changes': changes,
            'server_time': timezone.now().isoformat(),
            'changes_count': len(changes)
        })

    except Exception as e:
        print(f"❌ خطا در سینک پول: {e}")
        return Response({'status': 'error', 'message': str(e)})


@api_view(['POST'])
def sync_receive(request):
    """تأیید دریافت تغییرات - مارک کردن به عنوان سینک شده"""
    try:
        data = request.data
        tracker_id = data.get('tracker_id')

        if tracker_id:
            tracker = ChangeTracker.objects.get(id=tracker_id)
            tracker.sync_status = True  # تغییر از is_synced به sync_status
            tracker.save()

            return Response({
                'status': 'success',
                'message': f'تغییر {tracker_id} تأیید شد'
            })
        else:
            return Response({
                'status': 'error',
                'message': 'tracker_id الزامی است'
            }, status=400)

    except Exception as e:
        return Response({'status': 'error', 'message': str(e)}, status=400)


@api_view(['GET'])
def sync_model_data(request):
    """ارسال داده‌های کامل یک مدل خاص"""
    try:
        app_name = request.GET.get('app')
        model_name = request.GET.get('model')

        model_class = apps.get_model(app_name, model_name)
        records = list(model_class.objects.values())

        return Response({
            'status': 'success',
            'app': app_name,
            'model': model_name,
            'records_count': len(records),
            'records': records
        })

    except Exception as e:
        return Response({'status': 'error', 'message': str(e)})


@api_view(['POST'])
def receive_change(request):
    """دریافت تغییرات از لوکال‌ها و اعمال مستقیم در دیتابیس سرور"""
    try:
        data = request.data
        print(f"📥 دریافت تغییر از لوکال: {data}")

        app_name = data['app_name']
        model_name = data['model_name']
        record_id = data['record_id']
        action = data['action']
        change_data = data['data']

        # پیدا کردن مدل مربوطه
        model_class = apps.get_model(app_name, model_name)

        if action == 'delete':
            # حذف رکورد
            model_class.objects.filter(id=record_id).delete()
            print(f"🗑️ حذف در سرور: {app_name}.{model_name} - ID: {record_id}")

        else:
            # ایجاد یا آپدیت رکورد
            obj, created = model_class.objects.update_or_create(
                id=record_id,
                defaults=change_data
            )

            action_text = "ایجاد" if created else "آپدیت"
            print(f"✅ {action_text} در سرور: {app_name}.{model_name} - ID: {record_id}")

        return Response({
            'status': 'success',
            'message': f'تغییر {action} برای {model_name}-{record_id} اعمال شد'
        })

    except Exception as e:
        print(f"❌ خطا در پردازش تغییر از لوکال: {e}")
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=400)

@api_view(['GET'])
def get_changes(request):
    """ارسال تغییرات سرور به لوکال‌ها"""
    try:
        since = request.GET.get('since')

        queryset = ChangeTracker.objects.filter(
            sync_direction='server_to_local',
            created_at__gt=since if since else timezone.now() - timedelta(days=1)
        )

        changes = []
        for tracker in queryset:
            changes.append({
                'app_name': tracker.app_name,
                'model_name': tracker.model_name,
                'record_id': tracker.record_id,
                'action': tracker.action,
                'data': tracker.data,
                'created_at': tracker.created_at.isoformat()
            })

        return Response({
            'status': 'success',
            'changes': changes,
            'server_time': timezone.now().isoformat()
        })

    except Exception as e:
        return Response({'status': 'error', 'message': str(e)})


from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from cantact_app.models import Branch
from django.contrib.auth.models import User


@csrf_exempt
def sync_branches(request):
    """API برای دریافت لیست شعبه‌ها"""
    if request.method == 'GET':
        try:
            branches = Branch.objects.filter(is_active=True)
            branches_data = []

            for branch in branches:
                branches_data.append({
                    'id': branch.id,
                    'name': branch.name,
                    'code': branch.code,
                    'address': branch.address or '',
                    'phone': branch.phone or '',
                    'is_active': branch.is_active
                })

            return JsonResponse({
                'status': 'success',
                'branches': branches_data,
                'count': len(branches_data)
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            })
    return JsonResponse({'status': 'error', 'message': 'متد غیرمجاز'})


@csrf_exempt
def sync_users(request):
    """API برای دریافت لیست کاربران"""
    if request.method == 'GET':
        try:
            users = User.objects.filter(is_active=True)
            users_data = []

            for user in users:
                users_data.append({
                    'id': user.id,
                    'username': user.username,
                    'first_name': user.first_name or '',
                    'last_name': user.last_name or '',
                    'email': user.email or '',
                    'is_active': user.is_active,
                    'is_staff': user.is_staff,
                    'is_superuser': user.is_superuser
                })

            return JsonResponse({
                'status': 'success',
                'users': users_data,
                'count': len(users_data)
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            })
    return JsonResponse({'status': 'error', 'message': 'متد غیرمجاز'})