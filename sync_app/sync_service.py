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
                model_key = f"{app_name}.{model_name}".lower()  # تبدیل به حروف کوچک

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

        print(f"🔍 کشف شد: {len(sync_models)} مدل برای سینک")
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
            # افزایش timeout و غیرفعال کردن SSL verification
            response = requests.get(
                f"{self.server_url}/",
                timeout=30,
                verify=False  # غیرفعال کردن SSL verification
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

        # 1. ابتدا اتصال را بررسی کن
        if not self.check_internet_connection():
            return {'status': 'error', 'message': 'اتصال به سرور میسر نیست'}

        # 2. ارسال تغییرات لوکال به سرور
        sent_count = self.push_local_changes()

        # 3. دریافت تغییرات از سرور
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
        )

        unsynced_count = unsynced_logs.count()
        print(f"📝 تعداد تغییرات در انتظار ارسال: {unsynced_count}")

        if unsynced_count == 0:
            print("ℹ️ هیچ تغییری برای ارسال وجود ندارد")
            return 0

        # فقط 2 رکورد برای تست
        logs_to_sync = unsynced_logs.order_by('created_at')[:2]
        print(f"🔧 ارسال اولین {len(logs_to_sync)} تغییر برای تست...")

        sent_count = 0

        for log in logs_to_sync:
            try:
                # فرمت داده برای سرور
                sync_payload = {
                    'app_name': log.app_name,
                    'model_name': log.model_name,
                    'record_id': log.record_id,
                    'action': log.action,
                    'data': log.data or {},
                    'created_at': log.created_at.isoformat() if log.created_at else None,
                    'tracker_id': log.id,  # استفاده از tracker_id
                    'sync_direction': 'local_to_server'
                }

                print(f"🔍 ارسال داده برای {log.model_name}-{log.record_id}...")
                print(f"📦 payload: {sync_payload}")  # این خط را اضافه کنید

                # ارسال به سرور
                response = requests.post(
                    f"{self.server_url}/api/sync/receive/",
                    json=sync_payload,
                    timeout=30,
                    verify=False,
                    headers={'Content-Type': 'application/json'}
                )

                print(f"📡 وضعیت پاسخ: {response.status_code}")
                print(f"📄 محتوای پاسخ: {response.text}")  # این خط را اضافه کنید

                if response.status_code == 200:
                    response_data = response.json()
                    print(f"✅ پاسخ سرور: {response_data}")  # این خط را اضافه کنید
                    if response_data.get('status') == 'success':
                        log.sync_status = True
                        log.synced_at = timezone.now()
                        log.save()
                        sent_count += 1
                        print(f"✅ ارسال موفق: {log.model_name} - ID: {log.record_id}")
                    else:
                        print(f"⚠️ خطای سرور: {response_data.get('message')}")
                else:
                    print(f"❌ خطای HTTP {response.status_code}: {response.text}")

            except Exception as e:
                print(f"❌ خطا در ارسال {log.model_name}-{log.record_id}: {str(e)}")
                continue

        print(f"📤 ارسال کامل شد: {sent_count} از {len(logs_to_sync)}")
        return sent_count

    def pull_server_changes(self):
        """دریافت تغییرات از سرور"""
        print("📥 دریافت تغییرات از سرور...")

        try:
            # افزایش timeout و غیرفعال کردن SSL
            response = requests.get(
                f"{self.server_url}/api/sync/pull/",
                timeout=120,  # افزایش از 60 به 120 ثانیه
                verify=False
            )

            print(f"📡 وضعیت پاسخ سرور: {response.status_code}")

            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"📦 داده دریافتی: {data.get('message', 'بدون پیام')}")

                    if data.get('status') == 'success':
                        changes = data.get('changes', [])
                        print(f"🔄 تعداد تغییرات دریافتی: {len(changes)}")
                        return self.apply_server_changes(changes)
                    else:
                        print(f"❌ خطا در سرور: {data.get('message')}")
                except json.JSONDecodeError as e:
                    print(f"❌ خطا در پردازش JSON از سرور: {e}")
                    print(f"📄 محتوای پاسخ: {response.text}")

            elif response.status_code == 502:
                print("❌ خطای 502 - سرور overload شده است")
                print("💡 پیشنهاد: چند دقیقه صبر کنید و مجدداً تلاش کنید")
            elif response.status_code == 504:
                print("❌ خطای 504 - Gateway Timeout")
                print("💡 پیشنهاد: timeout را بیشتر کنید یا سرور را بهینه کنید")
            else:
                print(f"❌ خطای HTTP: {response.status_code}")
                print(f"📄 محتوای پاسخ: {response.text}")

        except requests.exceptions.Timeout:
            print("⏰ timeout در دریافت از سرور - سرور کند پاسخ می‌دهد")
            print("💡 پیشنهاد:")
            print("   - timeout را بیشتر کنید")
            print("   - در ساعت کم‌ترافیک سینک کنید")
            print("   - endpoint سرور را بهینه کنید")
        except requests.exceptions.ConnectionError:
            print("🔌 خطای اتصال - سرور در دسترس نیست")
        except Exception as e:
            print(f"❌ خطای غیرمنتظره در دریافت از سرور: {e}")

        return 0
    def apply_server_changes(self, changes):
        """اعمال تغییرات دریافتی از سرور با مدیریت وابستگی‌ها"""
        processed_count = 0

        print(f"📋 دریافت {len(changes)} تغییر از سرور")

        for change in changes:
            try:
                app_name = change['app_name']
                model_name = change['model_type']
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
                    # پردازش ویژه برای مدل‌های با وابستگی‌های پیچیده
                    if model_key == 'account_app.InventoryCount':
                        processed_data = self.process_inventory_count_data(data)
                    else:
                        processed_data = self._filter_and_convert_data(model_class, data, model_key)

                    if processed_data:
                        try:
                            obj, created = model_class.objects.update_or_create(
                                id=record_id,
                                defaults=processed_data
                            )
                            processed_count += 1
                            action_text = "ایجاد" if created else "آپدیت"
                            print(f"✅ {action_text}: {model_key} - ID: {record_id}")
                        except Exception as e:
                            # اگر خطا به دلیل وابستگی‌هاست، با مقادیر پیش‌فرض ذخیره کن
                            if "foreign key" in str(e).lower() or "branch" in str(e).lower() or "user" in str(
                                    e).lower():
                                processed_data = self.handle_foreign_key_fallback(model_key, data, record_id)
                                if processed_data:
                                    obj, created = model_class.objects.update_or_create(
                                        id=record_id,
                                        defaults=processed_data
                                    )
                                    processed_count += 1
                                    print(f"✅ {action_text} (با مقادیر پیش‌فرض): {model_key} - ID: {record_id}")
                            else:
                                raise e

            except Exception as e:
                print(f"❌ خطا در پردازش {model_key} - ID {record_id}: {str(e)}")
                continue

        print(f"🎯 اعمال شد: {processed_count} رکورد از سرور")
        return processed_count

    def _filter_and_convert_data(self, model_class, data, model_key):
        """فیلتر و تبدیل داده‌ها با مدیریت پیشرفته وابستگی‌ها"""
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

                # مدیریت ویژه فیلدهای ForeignKey
                if field.is_relation and field_name.endswith('_id'):
                    if self.check_foreign_key_exists(field, value):
                        filtered_data[field_name] = value
                    else:
                        # استفاده از مقدار پیش‌فرض برای وابستگی‌های از دست رفته
                        default_value = self.get_default_foreign_key(field_name, model_key)
                        if default_value is not None:
                            filtered_data[field_name] = default_value
                            print(f"⚠️ استفاده از مقدار پیش‌فرض برای {field_name}: {default_value}")
                        else:
                            print(f"⏭️ حذف فیلد {field_name} به دلیل عدم وجود وابستگی")
                        continue

                # بقیه تبدیل‌های عادی...
                # [کدهای موجود قبلی]

        except Exception as e:
            print(f"⚠️ خطا در فیلتر داده‌ها: {e}")
            # فال‌بک: استفاده از داده‌های خام
            for field_name, value in data.items():
                if value not in ["None", "null", None, ""]:
                    filtered_data[field_name] = value

        return filtered_data

    def check_foreign_key_exists(self, field, value):
        """بررسی وجود رکورد وابسته"""
        try:
            if hasattr(field, 'related_model') and field.related_model:
                return field.related_model.objects.filter(id=value).exists()
            return False
        except:
            return False

    def get_default_foreign_key(self, field_name, model_key):
        """دریافت مقدار پیش‌فرض برای فیلدهای وابسته"""
        try:
            if field_name == 'branch_id':
                from cantact_app.models import Branch
                default_branch = Branch.objects.first()
                return default_branch.id if default_branch else 1

            elif field_name in ['counter_id', 'user_id', 'created_by_id']:
                from django.contrib.auth.models import User
                default_user = User.objects.first()
                return default_user.id if default_user else 1

            elif field_name == 'product_id':
                from account_app.models import InventoryCount
                default_product = InventoryCount.objects.first()
                return default_product.id if default_product else 1

        except Exception as e:
            print(f"⚠️ خطا در دریافت پیش‌فرض برای {field_name}: {e}")

        return 1  # مقدار پیش‌فرض

    def process_inventory_count_data(self, data):
        """پردازش ویژه داده‌های InventoryCount با مدیریت وابستگی‌ها"""
        processed_data = {}

        # کپی فیلدهای مستقیم
        direct_fields = [
            'product_name', 'is_new', 'quantity', 'count_date',
            'created_at', 'barcode_data', 'selling_price', 'profit_percentage'
        ]

        for field in direct_fields:
            if field in data and data[field] is not None:
                processed_data[field] = data[field]

        # مدیریت وابستگی‌های ForeignKey
        branch_id = data.get('branch_id')
        counter_id = data.get('counter_id')

        # بررسی وجود Branch
        if branch_id:
            try:
                from cantact_app.models import Branch
                if Branch.objects.filter(id=branch_id).exists():
                    processed_data['branch_id'] = branch_id
                else:
                    # استفاده از شعبه پیش‌فرض
                    default_branch = Branch.objects.first()
                    if default_branch:
                        processed_data['branch_id'] = default_branch.id
                        print(f"⚠️ استفاده از شعبه پیش‌فرض برای InventoryCount")
                    else:
                        # ایجاد شعبه پیش‌فرض اگر وجود ندارد
                        default_branch = Branch.objects.create(
                            name="شعبه مرکزی",
                            address="آدرس پیش‌فرض",
                            phone="00000000000",
                            is_active=True
                        )
                        processed_data['branch_id'] = default_branch.id
                        print(f"✅ شعبه پیش‌فرض ایجاد شد")
            except Exception as e:
                print(f"⚠️ خطا در مدیریت شعبه: {e}")

        # بررسی وجود User
        if counter_id:
            try:
                from django.contrib.auth.models import User
                if User.objects.filter(id=counter_id).exists():
                    processed_data['counter_id'] = counter_id
                else:
                    # استفاده از کاربر پیش‌فرض
                    default_user = User.objects.first()
                    if default_user:
                        processed_data['counter_id'] = default_user.id
                        print(f"⚠️ استفاده از کاربر پیش‌فرض برای InventoryCount")
                    else:
                        # ایجاد کاربر پیش‌فرض اگر وجود ندارد
                        default_user = User.objects.create_user(
                            username='default_user',
                            password='default_pass',
                            first_name='کاربر',
                            last_name='پیش‌فرض'
                        )
                        processed_data['counter_id'] = default_user.id
                        print(f"✅ کاربر پیش‌فرض ایجاد شد")
            except Exception as e:
                print(f"⚠️ خطا در مدیریت کاربر: {e}")

        return processed_data

    def handle_foreign_key_fallback(self, model_key, data, record_id):
        """مدیریت fallback برای وابستگی‌های از دست رفته"""
        if model_key == 'account_app.InventoryCount':
            return self.process_inventory_count_data(data)

        # برای سایر مدل‌ها
        processed_data = {}
        for field_name, value in data.items():
            if not field_name.endswith('_id') or not isinstance(value, int):
                processed_data[field_name] = value

        return processed_data


    def _handle_required_fields(self, model_key, data):
        """مدیریت فیلدهای اجباری برای مدل‌های خاص"""
        # منطق مدیریت فیلدهای اجباری (همانند قبل)
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
        return self.bidirectional_sync()

    def upload_to_server(self):
        return self.push_local_changes()

    def download_from_server(self):
        result = self.pull_server_changes()
        return {'status': 'success', 'processed_count': result}



# ایجاد سرویس جهانی
sync_service = UniversalSyncService()

if not getattr(settings, 'SYNC_AUTO_START', True):
    print("🔴 سرویس سینک خودکار غیرفعال شده (در سطح ماژول)")
    sync_service.is_running = False