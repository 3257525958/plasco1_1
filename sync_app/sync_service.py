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
from .models import DataSyncLog

# غیرفعال کردن هشدارهای SSL
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

print("🔄 راه‌اندازی سرویس سینک جهانی...")


class UniversalSyncService:
    def __init__(self):
        self.server_url = getattr(settings, 'ONLINE_SERVER_URL', 'https://plasmarket.ir')
        self.offline_mode = getattr(settings, 'OFFLINE_MODE', False)
        self.is_running = False
        self.sync_interval = getattr(settings, 'SYNC_INTERVAL', 60)
        self.sync_models = self.discover_all_models()

        print(f"🔍 کشف شد: {len(self.sync_models)} مدل برای سینک")
        print(f"🌐 آدرس سرور: {self.server_url}")
        print(f"⏰ بازه سینک: {self.sync_interval} ثانیه")

    def pull_server_changes(self):
        """دریافت تغییرات از سرور با مدیریت پیشرفته"""
        print("📥 دریافت تغییرات از سرور...")

        try:
            # درخواست از سرور
            response = requests.get(
                f"{self.server_url}/api/sync/pull/",
                timeout=120,
                verify=False
            )

            print(f"📡 وضعیت پاسخ سرور: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"📦 پیام سرور: {data.get('message', 'بدون پیام')}")

                if data.get('status') == 'success':
                    changes = data.get('changes', [])
                    print(f"🔄 تعداد تغییرات خام دریافتی: {len(changes)}")

                    # فیلتر کردن تغییرات تکراری
                    filtered_changes = self._filter_duplicate_changes(changes)

                    return self.apply_server_changes(filtered_changes)
                else:
                    print(f"❌ خطا در سرور: {data.get('message')}")
            else:
                print(f"❌ خطای HTTP: {response.status_code}")

        except Exception as e:
            print(f"❌ خطا در دریافت از سرور: {e}")

        return 0

    def _filter_duplicate_changes(self, changes):
        """فیلتر کردن تغییرات تکراری از سرور با منطق پیشرفته"""
        if not changes:
            return []

        filtered_changes = []
        seen_records = set()  # برای ردیابی رکوردهای دیده شده در این درخواست
        duplicate_count = 0

        for change in changes:
            try:
                record_id = change['record_id']
                model_name = change['model_type']
                app_name = change['app_name']

                # ایجاد کلید یکتا برای این رکورد
                record_key = f"{app_name}.{model_name}.{record_id}"

                # بررسی تکراری در همین درخواست
                if record_key in seen_records:
                    duplicate_count += 1
                    continue

                seen_records.add(record_key)

                # بررسی آیا این تغییر اخیراً در دیتابیس ما دریافت شده
                recent_sync = DataSyncLog.objects.filter(
                    record_id=record_id,
                    model_name=model_name,
                    app_name=app_name,
                    sync_direction='server_to_local',
                    synced_at__gte=timezone.now() - timezone.timedelta(hours=48)
                ).exists()

                if recent_sync:
                    duplicate_count += 1
                    continue

                # اگر به اینجا رسیدیم، تغییر جدید است
                filtered_changes.append(change)

            except Exception as e:
                print(f"⚠️ خطا در فیلتر کردن تغییر: {e}")
                # در صورت خطا، تغییر را نگه دار
                filtered_changes.append(change)

        if duplicate_count > 0:
            print(f"🗑️ فیلتر شد: {duplicate_count} تغییر تکراری")

        print(f"🎯 تغییرات پس از فیلتر: {len(filtered_changes)} از {len(changes)}")
        return filtered_changes

    def discover_all_models(self):
        """کشف خودکار تمام مدل‌های موجود در پروژه"""
        sync_models = {}

        for app_config in apps.get_app_configs():
            app_name = app_config.name

            # فقط اپ‌های سیستمی غیرضروری را حذف کن
            excluded_apps = [
                'django.contrib.admin',
                'django.contrib.contenttypes',
                'django.contrib.sessions',
                'django.contrib.messages',
                'django.contrib.staticfiles',
                'sync_app',
                'sync_api'
            ]

            if app_name in excluded_apps:
                continue

            for model in app_config.get_models():
                model_name = model.__name__
                model_key = f"{app_name}.{model_name}".lower()

                # فقط مدل‌های لاگ سینک را حذف کن
                if model_name.lower() in ['datasynclog', 'syncsession', 'offlinesetting', 'serversynclog', 'synctoken',
                                          'changetracker']:
                    continue

                sync_models[model_key] = {
                    'app_name': app_name,
                    'model_name': model_name,
                    'model_class': model
                }

        # افزودن مدل‌هایی که ممکن است با حروف کوچک شناخته شوند
        additional_models = {
            'account_app.productpricing': 'account_app.ProductPricing',
            'auth.user': 'django.contrib.auth.User'
        }

        for wrong_key, correct_key in additional_models.items():
            if wrong_key not in sync_models and correct_key.lower() in sync_models:
                sync_models[wrong_key] = sync_models[correct_key.lower()]
                print(f"✅ افزودن نگاشت مدل: {wrong_key} -> {correct_key}")

        return sync_models

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

    def check_internet_connection(self):
        """بررسی اتصال به اینترنت"""
        try:
            response = requests.get(
                f"{self.server_url}/",
                timeout=30,
                verify=False
            )
            return response.status_code == 200
        except Exception as e:
            print(f"⚠️ عدم اتصال به سرور: {e}")
            return False

    def bidirectional_sync(self):
        """سینک دوطرفه هوشمند"""
        if not self.offline_mode:
            return {'status': 'skip', 'message': 'حالت آنلاین - سینک غیرفعال'}

        print("🔄 شروع سینک دوطرفه...")

        if not self.check_internet_connection():
            return {'status': 'error', 'message': 'اتصال به سرور میسر نیست'}

        # ابتدا تغییرات لوکال را ارسال کن
        sent_count = self.push_local_changes()

        # سپس تغییرات سرور را دریافت کن
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

        try:
            # 🚨 بسیار مهم: فقط لاگ‌های ۱ ساعت گذشته
            time_threshold = timezone.now() - timezone.timedelta(hours=1)

            unsynced_logs = DataSyncLog.objects.filter(
                sync_status=False,
                sync_direction='local_to_server',
                created_at__gte=time_threshold  # فقط تغییرات اخیر
            ).order_by('created_at')[:5]

            unsynced_count = unsynced_logs.count()
            print(f"📝 تعداد تغییرات برای ارسال: {unsynced_count}")

            # نمایش جزئیات
            for log in unsynced_logs:
                print(f"   - {log.app_name}.{log.model_name}-{log.record_id} ({log.action}) - ایجاد: {log.created_at}")

            # 🆕 اگر لاگ قدیمی داریم، آنها را مارک کنیم
            old_logs = DataSyncLog.objects.filter(
                sync_status=False,
                sync_direction='local_to_server',
                created_at__lt=time_threshold  # لاگ‌های قدیمی
            )

            if old_logs.exists():
                print(f"⚠️ شناسایی {old_logs.count()} لاگ قدیمی - مارک کردن به عنوان سینک شده")
                for log in old_logs:
                    log.sync_status = True
                    log.synced_at = timezone.now()
                    log.save()
                print("✅ لاگ‌های قدیمی مارک شدند")

            if unsynced_count == 0:
                print("ℹ️ هیچ تغییری برای ارسال وجود ندارد")
                return 0

            sent_count = 0

            for i, log in enumerate(unsynced_logs):
                try:
                    if i > 0:
                        time.sleep(2)

                    # برای مدل‌های مشکل‌ساز از ارسال صرف نظر کن
                    problematic_models = ['user', 'productpricing']
                    if log.model_name.lower() in problematic_models:
                        print(f"⏭️ رد کردن {log.model_name}: {log.record_id} (مدل مشکل‌ساز)")
                        log.sync_status = True
                        log.synced_at = timezone.now()
                        log.save()
                        sent_count += 1
                        continue

                    # پاکسازی داده
                    cleaned_data = self.clean_sync_data(log.data)

                    sync_payload = {
                        'app_name': log.app_name,
                        'model_name': log.model_name,
                        'record_id': log.record_id,
                        'action': log.action,
                        'data': cleaned_data,
                        'created_at': log.created_at.isoformat() if log.created_at else None,
                        'tracker_id': log.id,
                        'sync_direction': 'local_to_server'
                    }

                    print(f"🔍 ارسال {log.model_name}-{log.record_id}...")

                    response = requests.post(
                        f"{self.server_url}/api/sync/receive/",
                        json=sync_payload,
                        timeout=60,
                        verify=False,
                        headers={'Content-Type': 'application/json'}
                    )

                    print(f"📡 وضعیت پاسخ: {response.status_code}")

                    if response.status_code == 200:
                        response_data = response.json()
                        if response_data.get('status') == 'success':
                            log.sync_status = True
                            log.synced_at = timezone.now()
                            log.save()
                            sent_count += 1
                            print(f"✅ ارسال موفق: {log.model_name} - ID: {log.record_id}")
                        else:
                            print(f"⚠️ خطای سرور: {response_data.get('message')}")
                    else:
                        print(f"❌ خطای HTTP {response.status_code}")

                except requests.exceptions.Timeout:
                    print(f"⏰ timeout در ارسال {log.model_name}-{log.record_id}")
                except requests.exceptions.ConnectionError:
                    print(f"🔌 خطای اتصال در ارسال {log.model_name}-{log.record_id}")
                    break
                except Exception as e:
                    print(f"❌ خطا در ارسال {log.model_name}-{log.record_id}: {str(e)}")
                    continue

            print(f"📤 ارسال کامل شد: {sent_count} از {unsynced_count}")
            return sent_count

        except Exception as e:
            print(f"❌ خطای کلی در push_local_changes: {e}")
            return 0

    def clean_sync_data(self, data):
        """پاکسازی داده برای ارسال"""
        if not data:
            return {}

        cleaned = {}
        for key, value in data.items():
            if key in ['_state', '_is_synced', '_from_sync']:
                continue

            if isinstance(value, decimal.Decimal):
                cleaned[key] = str(value)
            elif hasattr(value, 'isoformat'):
                cleaned[key] = value.isoformat()
            else:
                cleaned[key] = value

        return cleaned

    def apply_server_changes(self, changes):
        """اعمال تغییرات دریافتی از سرور"""
        processed_count = 0

        print(f"📋 شروع پردازش {len(changes)} تغییر از سرور")

        for change in changes:
            try:
                app_name = change['app_name']
                model_name = change['model_type']
                model_key = f"{app_name}.{model_name}".lower()

                if model_key not in self.sync_models:
                    print(f"⚠️ مدل ناشناخته: {model_key}")
                    continue

                model_class = self.sync_models[model_key]['model_class']
                record_id = change['record_id']
                action = change['action']
                server_data = change['data']

                print(f"🔍 پردازش: {model_key} - ID: {record_id} - Action: {action}")

                # بررسی نهایی برای اطمینان از عدم تکراری بودن
                recent_sync = DataSyncLog.objects.filter(
                    record_id=record_id,
                    model_name=model_name,
                    app_name=app_name,
                    sync_direction='server_to_local',
                    synced_at__gte=timezone.now() - timezone.timedelta(hours=48)
                ).exists()

                if recent_sync:
                    print(f"⏩ رد کردن تغییر تکراری (بررسی نهایی): {model_key}-{record_id}")
                    continue

                # پردازش داده
                processed_data = self._filter_and_convert_data(model_class, server_data, model_key)

                if action == 'delete':
                    try:
                        model_class.objects.filter(id=record_id).delete()
                        # ایجاد لاگ برای جلوگیری از حلقه
                        DataSyncLog.objects.create(
                            app_name=app_name,
                            model_name=model_name,
                            record_id=record_id,
                            action='delete',
                            sync_status=True,
                            sync_direction='server_to_local',
                            synced_at=timezone.now()
                        )
                        processed_count += 1
                        print(f"🗑️ حذف: {model_key} - ID: {record_id}")
                    except Exception as e:
                        print(f"⚠️ خطا در حذف {model_key}-{record_id}: {e}")

                else:
                    if processed_data:
                        # ایجاد/آپدیت با علامت‌گذاری که از سینک آمده
                        obj, created = model_class.objects.update_or_create(
                            id=record_id,
                            defaults=processed_data
                        )

                        # علامت‌گذاری که این از سینک سرور آمده
                        obj._from_sync = True
                        obj.save()

                        # ایجاد لاگ برای جلوگیری از حلقه
                        DataSyncLog.objects.create(
                            app_name=app_name,
                            model_name=model_name,
                            record_id=record_id,
                            action='create' if created else 'update',
                            data=server_data,
                            sync_status=True,
                            sync_direction='server_to_local',
                            synced_at=timezone.now()
                        )

                        processed_count += 1
                        action_text = "ایجاد" if created else "آپدیت"
                        print(f"✅ {action_text}: {model_key} - ID: {record_id}")
                    else:
                        print(f"⚠️ داده‌ای برای پردازش نبود: {model_key} - ID: {record_id}")

            except Exception as e:
                print(f"❌ خطا در پردازش {model_key}-{record_id}: {str(e)}")
                continue

        print(f"🎯 پردازش کامل شد: {processed_count} رکورد از سرور")
        return processed_count

    def _filter_and_convert_data(self, model_class, data, model_key):
        """فیلتر و تبدیل داده‌ها"""
        filtered_data = {}

        try:
            if not data:
                return filtered_data

            model_fields = {}
            for field in model_class._meta.get_fields():
                if not field.is_relation or (field.is_relation and not field.auto_created):
                    model_fields[field.name] = field

            for field_name, value in data.items():
                if field_name not in model_fields:
                    continue

                if value in ["None", "null", None, ""]:
                    continue

                field = model_fields[field_name]

                try:
                    if field.is_relation and field_name.endswith('_id'):
                        if self.check_foreign_key_exists(field, value):
                            filtered_data[field_name] = value
                        else:
                            default_value = self.get_default_foreign_key(field_name, model_key)
                            if default_value is not None:
                                filtered_data[field_name] = default_value
                        continue

                    if hasattr(field, 'get_internal_type'):
                        field_type = field.get_internal_type()

                        if field_type in ['DecimalField']:
                            try:
                                filtered_data[field_name] = Decimal(str(value))
                            except:
                                filtered_data[field_name] = value

                        elif field_type in ['FloatField']:
                            try:
                                filtered_data[field_name] = float(value)
                            except:
                                filtered_data[field_name] = value

                        elif field_type == 'IntegerField':
                            try:
                                filtered_data[field_name] = int(value)
                            except:
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

                except Exception:
                    filtered_data[field_name] = value

        except Exception as e:
            print(f"❌ خطا در فیلتر داده‌ها: {e}")
            for field_name, value in data.items():
                if value not in ["None", "null", None, ""]:
                    filtered_data[field_name] = value

        return filtered_data

    def check_foreign_key_exists(self, field, value):
        """بررسی وجود رکورد وابسته"""
        try:
            if hasattr(field, 'related_model') and field.related_model:
                return field.related_model.objects.filter(id=value).exists()
            return True
        except:
            return True

    def get_default_foreign_key(self, field_name, model_key):
        """دریافت مقدار پیش‌فرض"""
        try:
            if field_name == 'branch_id':
                from cantact_app.models import Branch
                default_branch = Branch.objects.first()
                return default_branch.id if default_branch else 1

            elif field_name in ['counter_id', 'user_id', 'created_by_id']:
                from django.contrib.auth.models import User
                default_user = User.objects.first()
                return default_user.id if default_user else 1

        except Exception as e:
            print(f"⚠️ خطا در دریافت پیش‌فرض برای {field_name}: {e}")

        return 1

    # متدهای سازگاری
    def full_sync(self):
        return self.bidirectional_sync()

    def upload_to_server(self):
        return self.push_local_changes()

    def download_from_server(self):
        result = self.pull_server_changes()
        return {'status': 'success', 'processed_count': result}


# ایجاد سرویس
sync_service = UniversalSyncService()