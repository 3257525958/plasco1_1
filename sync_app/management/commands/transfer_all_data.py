#!/usr/bin/env python3
"""
اسکریپت انتقال کامل داده‌ها از سرور آنلاین به لوکال
این اسکریپت تمام مدل‌های مهم از اپ‌های مختلف را منتقل می‌کند
"""

import os
import sys
import django
import requests
import time
import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path

# تنظیمات Django
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'your_project.settings')
django.setup()

from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction
from django.apps import apps
import logging

# تنظیمات لاگ
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data_transfer.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class DataTransfer:
    """کلاس اصلی برای انتقال داده‌ها"""

    def __init__(self, online_server_url=None, api_token=None):
        self.online_server_url = online_server_url or settings.ONLINE_SERVER_URL
        self.api_token = api_token or getattr(settings, 'SYNC_API_TOKEN', '')
        self.headers = {
            'Authorization': f'Token {self.api_token}' if self.api_token else {},
            'Content-Type': 'application/json'
        }
        self.session = requests.Session()
        self.session.timeout = 60

        # آمار انتقال
        self.stats = {
            'total_transferred': 0,
            'total_errors': 0,
            'models': {}
        }

    def check_offline_mode(self):
        """بررسی حالت آفلاین"""
        if not getattr(settings, 'OFFLINE_MODE', False):
            logger.error("❌ این اسکریپت فقط در حالت آفلاین قابل اجراست")
            return False
        return True

    def fetch_data(self, endpoint, params=None):
        """دریافت داده از سرور"""
        try:
            url = f"{self.online_server_url}{endpoint}"
            response = self.session.get(
                url,
                params=params,
                headers=self.headers,
                timeout=90
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"❌ خطا در دریافت داده از {url}: {response.status_code}")
                return None

        except requests.exceptions.Timeout:
            logger.error(f"⏰ Timeout در دریافت داده از {endpoint}")
            return None
        except requests.exceptions.ConnectionError:
            logger.error(f"🔌 خطا در اتصال به سرور: {endpoint}")
            return None
        except Exception as e:
            logger.error(f"❌ خطای غیرمنتظره در دریافت {endpoint}: {e}")
            return None

    def transfer_users(self):
        """انتقال کاربران"""
        logger.info("🚀 شروع انتقال کاربران...")

        # دریافت کاربران از سرور
        data = self.fetch_data('/api/sync/user-data/')
        if not data:
            logger.warning("⚠️ استفاده از endpoint جایگزین برای کاربران...")
            data = self.fetch_data('/api/users/')

        if not data or data.get('status') != 'success':
            logger.error("❌ دریافت کاربران ناموفق بود")
            return 0, 0

        users_data = data.get('records', data.get('users', []))
        if not users_data:
            logger.warning("⚠️ هیچ کاربری در سرور یافت نشد")
            return 0, 0

        logger.info(f"📥 دریافت {len(users_data)} کاربر از سرور")

        saved = 0
        errors = 0

        for user_data in users_data:
            try:
                user_id = user_data.get('id')
                username = user_data.get('username')

                if not user_id or not username:
                    continue

                # بررسی وجود کاربر
                existing_user = User.objects.filter(id=user_id).first()

                # آماده‌سازی داده‌ها
                user_fields = {
                    'username': username,
                    'email': user_data.get('email', f'{username}@example.com'),
                    'first_name': user_data.get('first_name', ''),
                    'last_name': user_data.get('last_name', ''),
                    'is_active': user_data.get('is_active', True),
                    'is_staff': user_data.get('is_staff', False),
                    'is_superuser': user_data.get('is_superuser', False),
                }

                # مدیریت تاریخ‌ها
                if user_data.get('date_joined'):
                    try:
                        user_fields['date_joined'] = datetime.fromisoformat(
                            user_data['date_joined'].replace('Z', '+00:00')
                        )
                    except:
                        pass

                if existing_user:
                    # آپدیت کاربر موجود
                    for field, value in user_fields.items():
                        setattr(existing_user, field, value)
                    existing_user.save()
                else:
                    # ایجاد کاربر جدید با پسورد پیش‌فرض
                    user = User.objects.create_user(
                        id=user_id,
                        username=username,
                        password='default123',  # کاربر باید پسورد را تغییر دهد
                        **user_fields
                    )

                saved += 1

                if saved % 50 == 0:
                    logger.info(f"📝 {saved} کاربر پردازش شد...")

            except Exception as e:
                errors += 1
                if errors <= 5:
                    logger.error(f"❌ خطا در کاربر {user_data.get('username')}: {e}")

        # ایجاد ادمین اگر وجود ندارد
        if not User.objects.filter(username='admin').exists():
            try:
                User.objects.create_superuser(
                    username='admin',
                    email='admin@plasco.com',
                    password='admin123',
                    first_name='مدیر',
                    last_name='سیستم'
                )
                logger.info("✅ کاربر ادمین ایجاد شد")
            except Exception as e:
                logger.error(f"❌ خطا در ایجاد ادمین: {e}")

        logger.info(f"✅ انتقال کاربران کامل شد: {saved} ذخیره شده، {errors} خطا")
        return saved, errors

    def transfer_branches(self):
        """انتقال شعبه‌ها"""
        logger.info("🚀 شروع انتقال شعبه‌ها...")

        try:
            # دریافت شعبه‌ها از سرور
            data = self.fetch_data('/api/sync/model-data/', {
                'app': 'cantact_app',
                'model': 'Branch'
            })

            if not data or data.get('status') != 'success':
                logger.error("❌ دریافت شعبه‌ها ناموفق بود")
                return 0, 0

            branches_data = data.get('records', [])
            if not branches_data:
                logger.warning("⚠️ هیچ شعبه‌ای در سرور یافت نشد")
                return 0, 0

            logger.info(f"📥 دریافت {len(branches_data)} شعبه از سرور")

            from cantact_app.models import Branch

            saved = 0
            errors = 0

            for branch_data in branches_data:
                try:
                    branch_id = branch_data.get('id')
                    if not branch_id:
                        continue

                    # حذف فیلدهای غیرضروری
                    branch_clean = {k: v for k, v in branch_data.items()
                                    if not k.endswith('_id') or k == 'id'}

                    # ایجاد یا آپدیت شعبه
                    obj, created = Branch.objects.update_or_create(
                        id=branch_id,
                        defaults=branch_clean
                    )

                    saved += 1

                    if saved % 20 == 0:
                        logger.info(f"📝 {saved} شعبه پردازش شد...")

                except Exception as e:
                    errors += 1
                    if errors <= 5:
                        logger.error(f"❌ خطا در شعبه {branch_data.get('name')}: {e}")

            # ایجاد شعبه پیش‌فرض اگر وجود ندارد
            if not Branch.objects.exists():
                Branch.objects.create(
                    name='شعبه مرکزی',
                    code='001',
                    address='آدرس پیش‌فرض',
                    phone='02100000000',
                    is_active=True
                )
                logger.info("✅ شعبه پیش‌فرض ایجاد شد")

            logger.info(f"✅ انتقال شعبه‌ها کامل شد: {saved} ذخیره شده، {errors} خطا")
            return saved, errors

        except ImportError:
            logger.error("❌ مدل Branch یافت نشد. مطمئن شوید اپ cantact_app نصب شده است")
            return 0, 0
        except Exception as e:
            logger.error(f"❌ خطای غیرمنتظره در انتقال شعبه‌ها: {e}")
            return 0, 0

    def transfer_account_app_models(self):
        """انتقال تمام مدل‌های account_app"""
        logger.info("🚀 شروع انتقال مدل‌های account_app...")

        models_to_transfer = [
            'Product',
            'ProductPricing',
            'PaymentMethod',
            'Expense',
            'ExpenseImage',
            'StockTransaction',
            'InventoryCount'
        ]

        results = {}

        for model_name in models_to_transfer:
            try:
                logger.info(f"📦 انتقال {model_name}...")

                # دریافت مدل
                try:
                    model_class = apps.get_model('account_app', model_name)
                except LookupError:
                    logger.error(f"❌ مدل {model_name} یافت نشد")
                    results[model_name] = {'saved': 0, 'errors': 1}
                    continue

                # دریافت داده‌ها از سرور
                data = self.fetch_data('/api/sync/model-data/', {
                    'app': 'account_app',
                    'model': model_name
                })

                if not data or data.get('status') != 'success':
                    logger.error(f"❌ دریافت {model_name} ناموفق بود")
                    results[model_name] = {'saved': 0, 'errors': 1}
                    continue

                records = data.get('records', [])
                if not records:
                    logger.info(f"⚠️ هیچ رکوردی برای {model_name} یافت نشد")
                    results[model_name] = {'saved': 0, 'errors': 0}
                    continue

                logger.info(f"📥 دریافت {len(records)} رکورد برای {model_name}")

                saved = 0
                errors = 0

                # پردازش ویژه برای InventoryCount
                if model_name == 'InventoryCount':
                    saved, errors = self._save_inventory_counts(records)
                else:
                    saved, errors = self._save_general_records(model_class, records)

                results[model_name] = {'saved': saved, 'errors': errors}
                logger.info(f"✅ {model_name}: {saved} ذخیره، {errors} خطا")

                # استراحت بین مدل‌ها
                time.sleep(1)

            except Exception as e:
                logger.error(f"❌ خطا در انتقال {model_name}: {e}")
                results[model_name] = {'saved': 0, 'errors': 1}

        return results

    def _save_general_records(self, model_class, records):
        """ذخیره رکوردهای عمومی"""
        saved = 0
        errors = 0

        for record in records:
            try:
                record_id = record.get('id')
                if not record_id:
                    continue

                # حذف فیلدهای ForeignKey که ممکن است مشکل ایجاد کنند
                clean_data = {}
                for key, value in record.items():
                    if key.endswith('_id') and key not in ['id']:
                        continue
                    clean_data[key] = value

                # ایجاد یا آپدیت
                obj, created = model_class.objects.update_or_create(
                    id=record_id,
                    defaults=clean_data
                )

                saved += 1

                if saved % 100 == 0 and len(records) > 200:
                    logger.info(f"📝 {saved}/{len(records)} رکورد {model_class.__name__} پردازش شد...")

            except Exception as e:
                errors += 1
                if errors <= 3:
                    logger.error(f"❌ خطا در رکورد {record.get('id')}: {e}")

        return saved, errors

    def _save_inventory_counts(self, records):
        """ذخیره رکوردهای InventoryCount"""
        saved = 0
        errors = 0

        from cantact_app.models import Branch

        # دریافت یا ایجاد شعبه پیش‌فرض
        default_branch = Branch.objects.first()
        if not default_branch:
            default_branch = Branch.objects.create(
                name='شعبه مرکزی',
                code='001',
                address='آدرس پیش‌فرض',
                phone='02100000000',
                is_active=True
            )
            logger.info("✅ شعبه پیش‌فرض برای InventoryCount ایجاد شد")

        # دریافت یا ایجاد کاربر پیش‌فرض
        default_user = User.objects.filter(username='admin').first()
        if not default_user:
            default_user = User.objects.create_user(
                username='admin',
                password='admin123',
                email='admin@plasco.com',
                first_name='مدیر',
                last_name='سیستم',
                is_active=True,
                is_staff=True,
                is_superuser=True
            )
            logger.info("✅ کاربر پیش‌فرض برای InventoryCount ایجاد شد")

        for record in records:
            try:
                record_id = record.get('id')
                if not record_id:
                    continue

                # مدیریت branch
                branch_id = record.get('branch_id')
                if branch_id:
                    try:
                        branch = Branch.objects.get(id=branch_id)
                    except Branch.DoesNotExist:
                        branch = default_branch
                        logger.warning(f"⚠️ branch_id={branch_id} وجود ندارد، از پیش‌فرض استفاده شد")
                else:
                    branch = default_branch

                # مدیریت counter (user)
                counter_id = record.get('counter_id')
                if counter_id:
                    try:
                        counter = User.objects.get(id=counter_id)
                    except User.DoesNotExist:
                        counter = default_user
                        logger.warning(f"⚠️ counter_id={counter_id} وجود ندارد، از پیش‌فرض استفاده شد")
                else:
                    counter = default_user

                # آماده‌سازی داده‌ها
                from account_app.models import InventoryCount

                processed_data = {
                    'product_name': record.get('product_name', 'محصول ناشناخته'),
                    'is_new': record.get('is_new', True),
                    'quantity': record.get('quantity', 0),
                    'count_date': record.get('count_date', ''),
                    'barcode_data': record.get('barcode_data', ''),
                    'selling_price': record.get('selling_price', 0),
                    'branch': branch,
                    'counter': counter,
                    'profit_percentage': Decimal(str(record.get('profit_percentage', 70.00)))
                }

                # ایجاد یا آپدیت
                obj, created = InventoryCount.objects.update_or_create(
                    id=record_id,
                    defaults=processed_data
                )

                saved += 1

                if saved % 50 == 0 and len(records) > 100:
                    logger.info(f"📝 {saved}/{len(records)} رکورد InventoryCount پردازش شد...")

            except Exception as e:
                errors += 1
                if errors <= 5:
                    logger.error(f"❌ خطا در InventoryCount رکورد {record.get('id')}: {e}")

        return saved, errors

    def cleanup_extra_data(self):
        """پاکسازی داده‌های اضافه"""
        logger.info("🧹 شروع پاکسازی داده‌های اضافه...")

        cleanup_results = {}

        # پاکسازی کاربران اضافه
        cleanup_results['User'] = self._cleanup_users()

        # پاکسازی سایر مدل‌ها
        models_to_cleanup = [
            ('cantact_app', 'Branch'),
            ('account_app', 'Product'),
            ('account_app', 'ProductPricing'),
            ('account_app', 'PaymentMethod'),
            ('account_app', 'Expense'),
            ('account_app', 'ExpenseImage'),
            ('account_app', 'StockTransaction'),
            ('account_app', 'InventoryCount'),
        ]

        for app_label, model_name in models_to_cleanup:
            try:
                count = self._cleanup_model(app_label, model_name)
                cleanup_results[model_name] = count
                if count > 0:
                    logger.info(f"🧹 {model_name}: {count} رکورد پاک شد")
            except Exception as e:
                logger.error(f"⚠️ خطا در پاکسازی {model_name}: {e}")
                cleanup_results[model_name] = 0

        return cleanup_results

    def _cleanup_users(self):
        """پاکسازی کاربران اضافه"""
        try:
            # دریافت IDهای کاربران از سرور
            data = self.fetch_data('/api/sync/user-data/')
            if not data or data.get('status') != 'success':
                return 0

            server_users = data.get('records', data.get('users', []))
            server_ids = {u['id'] for u in server_users if u.get('id')}

            # کاربران محلی
            local_ids = set(User.objects.values_list('id', flat=True))

            # پیدا کردن کاربران اضافه (بدون در نظر گرفتن کاربران سیستمی)
            extra_ids = local_ids - server_ids

            # حذف کاربران سیستمی از لیست حذف
            system_users = User.objects.filter(username__in=['admin', 'superuser', 'administrator'])
            system_ids = set(system_users.values_list('id', flat=True))
            extra_ids = extra_ids - system_ids

            if not extra_ids:
                return 0

            # حذف کاربران اضافه
            deleted_count, _ = User.objects.filter(id__in=extra_ids).delete()
            return deleted_count

        except Exception as e:
            logger.error(f"❌ خطا در پاکسازی کاربران: {e}")
            return 0

    def _cleanup_model(self, app_label, model_name):
        """پاکسازی یک مدل خاص"""
        try:
            # دریافت IDها از سرور
            data = self.fetch_data('/api/sync/model-data/', {
                'app': app_label,
                'model': model_name
            })

            if not data or data.get('status') != 'success':
                return 0

            records = data.get('records', [])
            server_ids = {r['id'] for r in records if r.get('id')}

            # دریافت مدل
            model_class = apps.get_model(app_label, model_name)
            local_ids = set(model_class.objects.values_list('id', flat=True))

            # پیدا کردن IDهای اضافه
            extra_ids = local_ids - server_ids

            if not extra_ids:
                return 0

            # حذف
            deleted_count, _ = model_class.objects.filter(id__in=extra_ids).delete()
            return deleted_count

        except Exception as e:
            logger.error(f"❌ خطا در پاکسازی {model_name}: {e}")
            return 0

    def generate_report(self, user_stats, branch_stats, account_results, cleanup_results):
        """تولید گزارش نهایی"""
        logger.info("\n" + "=" * 60)
        logger.info("📋 گزارش نهایی انتقال داده")
        logger.info("=" * 60)

        # جمع آوری آمار
        total_saved = 0
        total_errors = 0

        # کاربران
        if user_stats:
            logger.info(f"\n👥 کاربران:")
            logger.info(f"   ✅ ذخیره شده: {user_stats[0]}")
            logger.info(f"   ❌ خطاها: {user_stats[1]}")
            total_saved += user_stats[0]
            total_errors += user_stats[1]

        # شعبه‌ها
        if branch_stats:
            logger.info(f"\n🏢 شعبه‌ها:")
            logger.info(f"   ✅ ذخیره شده: {branch_stats[0]}")
            logger.info(f"   ❌ خطاها: {branch_stats[1]}")
            total_saved += branch_stats[0]
            total_errors += branch_stats[1]

        # مدل‌های account_app
        if account_results:
            logger.info(f"\n📊 مدل‌های account_app:")
            for model_name, stats in account_results.items():
                logger.info(f"   📦 {model_name}:")
                logger.info(f"      ✅ ذخیره شده: {stats['saved']}")
                logger.info(f"      ❌ خطاها: {stats['errors']}")
                total_saved += stats['saved']
                total_errors += stats['errors']

        # پاکسازی
        if cleanup_results:
            logger.info(f"\n🧹 پاکسازی:")
            total_cleaned = 0
            for model_name, count in cleanup_results.items():
                if count > 0:
                    logger.info(f"   {model_name}: {count} رکورد حذف شد")
                    total_cleaned += count

            if total_cleaned == 0:
                logger.info("   ✅ هیچ داده اضافه‌ای یافت نشد")

        # جمع کل
        logger.info("\n" + "=" * 60)
        logger.info(f"📈 جمع کل انتقال: {total_saved} رکورد")
        logger.info(f"❌ جمع کل خطاها: {total_errors} خطا")

        if cleanup_results:
            logger.info(f"🗑️  جمع کل پاک‌سازی: {sum(cleanup_results.values())} رکورد")

        # بررسی ویژه
        logger.info("\n🔍 بررسی ویژه:")
        try:
            from account_app.models import InventoryCount
            inv_count = InventoryCount.objects.count()
            logger.info(f"   📊 تعداد InventoryCount: {inv_count}")

            from cantact_app.models import Branch
            branch_count = Branch.objects.count()
            logger.info(f"   🏢 تعداد شعبه‌ها: {branch_count}")

            user_count = User.objects.count()
            logger.info(f"   👤 تعداد کاربران: {user_count}")

        except Exception as e:
            logger.error(f"   ⚠️ خطا در بررسی ویژه: {e}")

        logger.info("=" * 60)

    def run_full_transfer(self, skip_cleanup=False):
        """اجرای کامل انتقال"""
        logger.info("🚀 شروع فرآیند انتقال کامل داده‌ها...")
        start_time = time.time()

        # بررسی حالت آفلاین
        if not self.check_offline_mode():
            return False

        try:
            # مرحله 1: انتقال کاربران
            logger.info("\n🔗 مرحله 1: انتقال کاربران")
            user_stats = self.transfer_users()

            # مرحله 2: انتقال شعبه‌ها
            logger.info("\n🔗 مرحله 2: انتقال شعبه‌ها")
            branch_stats = self.transfer_branches()

            # مرحله 3: انتقال مدل‌های account_app
            logger.info("\n🔗 مرحله 3: انتقال مدل‌های account_app")
            account_results = self.transfer_account_app_models()

            # مرحله 4: پاکسازی (اختیاری)
            cleanup_results = {}
            if not skip_cleanup:
                logger.info("\n🔗 مرحله 4: پاکسازی داده‌های اضافه")
                cleanup_results = self.cleanup_extra_data()

            # مرحله 5: گزارش
            logger.info("\n🔗 مرحله 5: تولید گزارش")
            self.generate_report(user_stats, branch_stats, account_results, cleanup_results)

            # محاسبه زمان
            elapsed_time = time.time() - start_time
            logger.info(f"\n⏱️  زمان اجرا: {elapsed_time:.2f} ثانیه")

            logger.info("\n🎉 انتقال داده‌ها با موفقیت انجام شد!")
            return True

        except KeyboardInterrupt:
            logger.warning("\n⚠️ عملیات توسط کاربر لغو شد")
            return False
        except Exception as e:
            logger.error(f"\n❌ خطای غیرمنتظره: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """تابع اصلی اجرا"""
    import argparse

    parser = argparse.ArgumentParser(description='انتقال کامل داده‌ها از سرور آنلاین به لوکال')
    parser.add_argument('--skip-cleanup', action='store_true',
                        help='رد کردن مرحله پاکسازی')
    parser.add_argument('--server-url', type=str,
                        help='آدرس سرور آنلاین (اختیاری)')
    parser.add_argument('--api-token', type=str,
                        help='توکن API (اختیاری)')
    parser.add_argument('--models-only', action='store_true',
                        help='فقط انتقال مدل‌ها (بدون کاربران و شعبه‌ها)')

    args = parser.parse_args()

    # ایجاد شیء انتقال
    transfer = DataTransfer(
        online_server_url=args.server_url,
        api_token=args.api_token
    )

    if args.models_only:
        # فقط انتقال مدل‌های account_app
        logger.info("🚀 شروع انتقال مدل‌های account_app...")
        results = transfer.transfer_account_app_models()
        transfer.generate_report(None, None, results, {})
    else:
        # انتقال کامل
        transfer.run_full_transfer(skip_cleanup=args.skip_cleanup)

    logger.info("✨ عملیات به پایان رسید")


if __name__ == "__main__":
    main()