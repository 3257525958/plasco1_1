from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings


class Command(BaseCommand):
    help = 'همگام‌سازی ترتیبی تمام داده‌ها - بدون پیش‌فرض'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='اجرای اجباری حتی اگر خطایی رخ دهد',
        )

    def handle(self, *args, **options):
        force_mode = options.get('force', False)

        self.stdout.write("=" * 70)
        self.stdout.write("🚀 سیستم همگام‌سازی ترتیبی Plasco")
        self.stdout.write("=" * 70)

        # لیست دستورات به ترتیب اجرا
        sync_commands = [
            ('sync_full_cantact', 'cantact_app', 'کاربران و شعبه‌ها'),
            ('sync_full_account', 'account_app', 'محصولات و انبار'),
            ('sync_full_dashbord', 'dashbord_app', 'داشبورد'),
            ('sync_full_invoice', 'invoice_app', 'فاکتورها'),
            ('sync_full_pos_payment', 'pos_payment', 'پرداخت‌ها'),
        ]

        results = []

        for command_name, app_name, description in sync_commands:
            self.stdout.write(f"\n📦 مرحله: همگام‌سازی {description} ({app_name})")
            self.stdout.write("-" * 50)

            try:
                # بررسی وجود دستور
                call_command(command_name, '--help', stdout=self.stdout, stderr=self.stdout)

                # اجرای دستور
                self.stdout.write(f"🎯 اجرای دستور: {command_name}")
                call_command(command_name)

                results.append((command_name, '✅ موفق', ''))
                self.stdout.write(f"✅ {command_name} با موفقیت اجرا شد")

            except Exception as e:
                error_msg = str(e)
                results.append((command_name, '❌ خطا', error_msg))
                self.stdout.write(f"❌ خطا در {command_name}: {error_msg}")

                if not force_mode:
                    self.stdout.write("\n⚠️ توقف به دلیل خطا (برای ادامه از --force استفاده کنید)")
                    break

        # گزارش نهایی
        self.stdout.write("\n" + "=" * 70)
        self.stdout.write("📋 گزارش نهایی همگام‌سازی")
        self.stdout.write("=" * 70)

        successful = sum(1 for _, status, _ in results if status == '✅ موفق')
        failed = sum(1 for _, status, _ in results if status == '❌ خطا')

        self.stdout.write(f"\n📊 آمار:")
        self.stdout.write(f"   ✅ موفق: {successful}")
        self.stdout.write(f"   ❌ ناموفق: {failed}")
        self.stdout.write(f"   📈 مجموع: {len(sync_commands)}")

        self.stdout.write("\n📋 جزئیات:")
        for command_name, status, error in results:
            if error:
                self.stdout.write(f"   {command_name}: {status} - {error}")
            else:
                self.stdout.write(f"   {command_name}: {status}")

        if failed == 0:
            self.stdout.write("\n🎉 تمام مراحل با موفقیت انجام شد!")
        elif force_mode:
            self.stdout.write("\n⚠️ برخی مراحل با خطا مواجه شدند اما ادامه یافت!")
        else:
            self.stdout.write("\n❌ همگام‌سازی متوقف شد. لطفاً خطاها را برطرف کنید.")

        self.stdout.write("\n💡 نکات:")
        self.stdout.write("1. ترتیب اجرا مهم است: ابتدا کاربران و شعبه‌ها، سپس محصولات")
        self.stdout.write("2. برای اجرای اجباری: python manage.py sync_sequential --force")
        self.stdout.write("3. برای اجرای دستی هر بخش: python manage.py sync_full_cantact")

        return successful == len(sync_commands)