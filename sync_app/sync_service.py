# sync_app/sync_service.py
import requests
import json
import time
import decimal
import threading
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.apps import apps

# import های داخلی sync_app
from .models import DataSyncLog

print("🔄 راه‌اندازی سرویس سینک جهانی...")


class UniversalSyncService:
    def __init__(self):
        self.server_url = getattr(settings, 'ONLINE_SERVER_URL', 'https://plasmarket.ir')
        self.offline_mode = getattr(settings, 'OFFLINE_MODE', False)
        self.is_running = False
        self.sync_interval = getattr(settings, 'SYNC_INTERVAL', 300)  # 5 دقیقه پیش‌فرض
        self.sync_models = self.discover_all_models()

        print(f"🔍 کشف شد: {len(self.sync_models)} مدل برای سینک")
        print(f"🌐 آدرس سرور: {self.server_url}")
        print(f"⏰ بازه سینک: {self.sync_interval} ثانیه")

    def start_auto_sync(self):
        """شروع سینک خودکار در فواصل زمانی"""
        if not getattr(settings, 'SYNC_AUTO_START', True):
            print("🔴 سرویس سینک خودکار غیرفعال شده")
            return

        if self.is_running:
            return

        self.is_running = True
        print(f"🔄 سرویس سینک خودکار فعال شد (هر {self.sync_interval} ثانیه)")

        def sync_loop():
            while self.is_running:
                try:
                    print("⏰ شروع سینک دوره‌ای...")
                    result = self.bidirectional_sync()
                    print(f"✅ سینک دوره‌ای انجام شد: {result}")
                except Exception as e:
                    print(f"❌ خطا در سینک دوره‌ای: {e}")

                time.sleep(self.sync_interval)

        threading.Thread(target=sync_loop, daemon=True).start()

    def stop_auto_sync(self):
        """توقف سرویس سینک"""
        self.is_running = False
        print("🛑 سرویس سینک خودکار متوقف شد")

    def discover_all_models(self):
        """کشف خودکار تمام مدل‌های موجود در پروژه"""
        sync_models = {}

        for app_config in apps.get_app_configs():
            app_name = app_config.name
            if any(app_name.startswith(excluded) for excluded in [
                'django.contrib.admin', 'django.contrib.auth',
                'django.contrib.contenttypes', 'django.contrib.sessions',
                'django.contrib.messages', 'django.contrib.staticfiles',
                'sync_app', 'sync_api'
            ]):
                continue

            for model in app_config.get_models():
                model_name = model.__name__
                model_key = f"{app_name}.{model_name}"

                if model_name in ['DataSyncLog', 'SyncSession', 'OfflineSetting', 'ServerSyncLog', 'SyncToken']:
                    continue

                sync_models[model_key] = {
                    'app_name': app_name,
                    'model_name': model_name,
                    'model_class': model
                }

        return sync_models

    def check_internet_connection(self):
        """بررسی اتصال به اینترنت"""
        try:
            response = requests.get(f"{self.server_url}/", timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"⚠️ عدم اتصال به سرور: {e}")
            return False

    def bidirectional_sync(self):
        """سینک دوطرفه هوشمند"""
        if not self.offline_mode:
            return {'status': 'skip', 'message': 'حالت آنلاین - سینک غیرفعال'}

        if not self.check_internet_connection():
            return {'status': 'error', 'message': 'اتصال به سرور میسر نیست'}

        print("🔄 شروع سینک دوطرفه...")

        # 1. ارسال تغییرات لوکال به سرور
        sent_count = self.push_local_changes()

        # 2. دریافت تغییرات از سرور
        received_count = self.pull_server_changes()

        return {
            'sent_to_server': sent_count,
            'received_from_server': received_count,
            'total': sent_count + received_count
        }

    def push_local_changes(self):
        """ارسال تغییرات لوکال به سرور"""
        if not self.offline_mode:
            return 0

        print("📤 ارسال تغییرات لوکال به سرور...")

        unsynced_logs = DataSyncLog.objects.filter(
            sync_status=False,
            sync_direction='local_to_server'
        ).order_by('created_at')[:100]

        sent_count = 0

        for log in unsynced_logs:
            try:
                sync_payload = {
                    'local_log_id': log.id,
                    'app_name': log.app_name,
                    'model_name': log.model_name,
                    'record_id': log.record_id,
                    'action': log.action,
                    'data': log.data,
                    'created_at': log.created_at.isoformat(),
                    'branch_id': log.branch_id
                }

                response = requests.post(
                    f"{self.server_url}/api/sync/receive/",  # استفاده از endpoint موجود
                    json=sync_payload,
                    timeout=30
                )

                if response.status_code == 200:
                    log.sync_status = True
                    log.synced_at = timezone.now()
                    log.save()
                    sent_count += 1
                    print(f"✅ ارسال شد: {log.model_name} - ID: {log.record_id}")

            except Exception as e:
                print(f"❌ خطا در ارسال {log.model_name}-{log.record_id}: {str(e)}")
                continue

        return sent_count

    def pull_server_changes(self):
        """دریافت تغییرات از سرور"""
        print("📥 دریافت تغییرات از سرور...")

        try:
            response = requests.get(
                f"{self.server_url}/api/sync/pull/",  # استفاده از endpoint موجود
                timeout=60
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    changes = data.get('changes', [])
                    return self.apply_server_changes(changes)
                else:
                    print(f"❌ خطا در سرور: {data.get('message')}")
            else:
                print(f"❌ خطای HTTP: {response.status_code}")

        except Exception as e:
            print(f"❌ خطا در دریافت از سرور: {e}")

        return 0

    def apply_server_changes(self, changes):
        """اعمال تغییرات دریافتی از سرور"""
        processed_count = 0

        print(f"📋 دریافت {len(changes)} تغییر از سرور")

        for change in changes:
            try:
                app_name = change['app_name']
                model_name = change['model_type']  # توجه: model_type نه model_name
                model_key = f"{app_name}.{model_name}"

                if model_key not in self.sync_models:
                    print(f"⚠️ مدل ناشناخته: {model_key}")
                    continue

                model_class = self.sync_models[model_key]['model_class']
                record_id = change['record_id']
                action = change['action']
                data = change['data']

                if action == 'delete':
                    model_class.objects.filter(id=record_id).delete()
                    processed_count += 1
                    print(f"🗑️ حذف: {model_key} - ID: {record_id}")
                else:
                    filtered_data = self._filter_and_convert_data(model_class, data, model_key)

                    if filtered_data:
                        obj, created = model_class.objects.update_or_create(
                            id=record_id,
                            defaults=filtered_data
                        )

                        processed_count += 1
                        action_text = "ایجاد" if created else "آپدیت"
                        print(f"✅ {action_text}: {model_key} - ID: {record_id}")

            except Exception as e:
                print(f"❌ خطا در پردازش {model_key} - ID {record_id}: {str(e)}")
                continue

        print(f"🎯 اعمال شد: {processed_count} رکورد از سرور")
        return processed_count

    def _filter_and_convert_data(self, model_class, data, model_key):
        """فیلتر و تبدیل داده‌ها به انواع صحیح"""
        filtered_data = {}

        try:
            model_fields = {}
            for field in model_class._meta.get_fields():
                if not field.is_relation or (field.is_relation and not field.auto_created):
                    model_fields[field.name] = field

            for field_name, value in data.items():
                if field_name not in model_fields:
                    continue

                field = model_fields[field_name]

                if value in ["None", "null", None, ""]:
                    continue

                try:
                    if hasattr(field, 'get_internal_type'):
                        field_type = field.get_internal_type()

                        if field_type in ['DecimalField', 'FloatField']:
                            try:
                                filtered_data[field_name] = float(value)
                            except (ValueError, TypeError):
                                filtered_data[field_name] = value

                        elif field_type == 'IntegerField':
                            try:
                                filtered_data[field_name] = int(value)
                            except (ValueError, TypeError):
                                filtered_data[field_name] = value

                        elif field_type == 'BooleanField':
                            if isinstance(value, str):
                                filtered_data[field_name] = value.lower() in ['true', '1', 'yes', 'y']
                            else:
                                filtered_data[field_name] = bool(value)
                        else:
                            filtered_data[field_name] = value
                    else:
                        filtered_data[field_name] = value

                except (ValueError, TypeError) as e:
                    print(f"⚠️ خطا در تبدیل فیلد {field_name}: {value} -> {e}")
                    filtered_data[field_name] = value
                    continue

        except Exception as e:
            print(f"⚠️ خطا در فیلتر داده‌ها: {e}")
            for field_name, value in data.items():
                if value not in ["None", "null", None, ""]:
                    filtered_data[field_name] = value

        filtered_data = self._handle_required_fields(model_key, filtered_data)
        return filtered_data

    def _handle_required_fields(self, model_key, data):
        """مدیریت فیلدهای اجباری برای مدل‌های خاص"""
        if model_key == 'account_app.InventoryCount':
            if 'branch_id' not in data:
                try:
                    from cantact_app.models import Branch
                    default_branch = Branch.objects.first()
                    if default_branch:
                        data['branch_id'] = default_branch.id
                except Exception as e:
                    print(f"⚠️ خطا در دریافت شعبه پیش‌فرض برای InventoryCount: {e}")

        elif model_key == 'invoice_app.Invoicefrosh':
            if 'branch_id' not in data:
                try:
                    from cantact_app.models import Branch
                    default_branch = Branch.objects.first()
                    if default_branch:
                        data['branch_id'] = default_branch.id
                except Exception as e:
                    print(f"⚠️ خطا در دریافت شعبه پیش‌فرض: {e}")

            if 'created_by_id' not in data:
                try:
                    from django.contrib.auth.models import User
                    default_user = User.objects.first()
                    if default_user:
                        data['created_by_id'] = default_user.id
                except Exception as e:
                    print(f"⚠️ خطا در دریافت کاربر پیش‌فرض: {e}")

        elif model_key == 'account_app.Expense':
            if 'branch_id' not in data:
                try:
                    from cantact_app.models import Branch
                    default_branch = Branch.objects.first()
                    if default_branch:
                        data['branch_id'] = default_branch.id
                except Exception as e:
                    print(f"⚠️ خطا در دریافت شعبه پیش‌فرض برای Expense: {e}")

            if 'user_id' not in data:
                try:
                    from django.contrib.auth.models import User
                    default_user = User.objects.first()
                    if default_user:
                        data['user_id'] = default_user.id
                except Exception as e:
                    print(f"⚠️ خطا در دریافت کاربر پیش‌فرض برای Expense: {e}")

        return data

    # متدهای قدیمی برای سازگاری
    def full_sync(self):
        """سینک کامل (برای سازگاری با کد قدیمی)"""
        return self.bidirectional_sync()

    def upload_to_server(self):
        """ارسال تغییرات (برای سازگاری با کد قدیمی)"""
        return self.push_local_changes()

    def download_from_server(self):
        """دریافت تغییرات (برای سازگاری با کد قدیمی)"""
        result = self.pull_server_changes()
        return {'status': 'success', 'processed_count': result}


# ایجاد سرویس جهانی
sync_service = UniversalSyncService()

# غیرفعال کردن شروع خودکار سرویس اگر تنظیم شده باشد
if not getattr(settings, 'SYNC_AUTO_START', True):
    print("🔴 سرویس سینک خودکار غیرفعال شده (در سطح ماژول)")
    sync_service.is_running = False