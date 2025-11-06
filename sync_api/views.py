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
    """ارسال تغییرات از سرور به لوکال - مبتنی بر ChangeTracker"""
    try:
        last_sync_str = request.GET.get('last_sync')
        last_sync = timezone.datetime.fromisoformat(last_sync_str) if last_sync_str else None

        print(f"📤 ارسال تغییرات از سرور - آخرین سینک: {last_sync}")

        # پیدا کردن تغییرات جدید
        if last_sync:
            changes_tracked = ChangeTracker.objects.filter(
                created_at__gt=last_sync,  # تغییر از changed_at به created_at
                sync_status=False  # تغییر از is_synced به sync_status
            )
        else:
            changes_tracked = ChangeTracker.objects.filter(sync_status=False)  # تغییر از is_synced به sync_status

        changes = []
        for tracker in changes_tracked:
            try:
                model_class = apps.get_model(tracker.app_name, tracker.model_name)

                if tracker.action == 'delete':
                    # برای حذف، فقط اطلاعات پایه بفرست
                    changes.append({
                        'app_name': tracker.app_name,
                        'model_type': tracker.model_name,
                        'record_id': tracker.record_id,
                        'action': 'delete',
                        'data': {'id': tracker.record_id},
                        'tracker_id': tracker.id,
                        'changed_at': tracker.created_at.isoformat()  # تغییر از changed_at به created_at
                    })
                else:
                    # برای ایجاد/آپدیت، داده کامل بفرست
                    obj = model_class.objects.get(id=tracker.record_id)
                    data = {}
                    for field in obj._meta.get_fields():
                        if not field.is_relation or field.one_to_one:
                            try:
                                value = getattr(obj, field.name)
                                if hasattr(value, 'isoformat'):
                                    data[field.name] = value.isoformat()
                                elif isinstance(value, (int, float, bool)):
                                    data[field.name] = value
                                else:
                                    data[field.name] = str(value)
                            except:
                                data[field.name] = None

                    changes.append({
                        'app_name': tracker.app_name,
                        'model_type': tracker.model_name,
                        'record_id': tracker.record_id,
                        'action': tracker.action,
                        'data': data,
                        'tracker_id': tracker.id,
                        'changed_at': tracker.created_at.isoformat()  # تغییر از changed_at به created_at
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