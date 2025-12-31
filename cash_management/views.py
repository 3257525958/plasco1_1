
# -----------------------------سرمایه گزاری------------------------------------------------------
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

from .forms import InvestmentForm
from .models import Investment
from cantact_app.models import accuntmodel
from invoice_app.models import Paymentnumber


def number_to_words(num):
    """تبدیل عدد به حروف فارسی - نسخه ساده"""
    if num == 0:
        return 'صفر'

    # واحدها
    ones = ['', 'یک', 'دو', 'سه', 'چهار', 'پنج', 'شش', 'هفت', 'هشت', 'نه']
    tens = ['', 'ده', 'بیست', 'سی', 'چهل', 'پنجاه', 'شصت', 'هفتاد', 'هشتاد', 'نود']
    hundreds = ['', 'صد', 'دویست', 'سیصد', 'چهارصد', 'پانصد', 'ششصد', 'هفتصد', 'هشتصد', 'نهصد']
    teens = ['ده', 'یازده', 'دوازده', 'سیزده', 'چهارده', 'پانزده', 'شانزده', 'هفده', 'هجده', 'نوزده']

    def convert_three_digits(n):
        """تبدیل سه رقم به حروف"""
        result = ''

        # صدگان
        if n >= 100:
            result += hundreds[n // 100] + ' و '
            n %= 100

        # دهگان و یکان
        if n >= 20:
            result += tens[n // 10]
            if n % 10 > 0:
                result += ' و ' + ones[n % 10]
        elif n >= 10:
            result += teens[n - 10]
        elif n > 0:
            result += ones[n]

        return result.rstrip(' و ')

    # جداکننده هزارگان
    result = ''

    # میلیارد
    if num >= 1000000000:
        result += convert_three_digits(num // 1000000000) + ' میلیارد و '
        num %= 1000000000

    # میلیون
    if num >= 1000000:
        result += convert_three_digits(num // 1000000) + ' میلیون و '
        num %= 1000000

    # هزار
    if num >= 1000:
        thousand_part = num // 1000
        if thousand_part == 1:
            result += 'هزار و '
        else:
            result += convert_three_digits(thousand_part) + ' هزار و '
        num %= 1000

    # واحد
    if num > 0:
        result += convert_three_digits(num)

    # حذف " و " اضافی در انتها
    result = result.rstrip(' و ')

    return result + ' تومان'


@csrf_exempt
def check_melicode(request):
    """بررسی وجود کد ملی در دیتابیس"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            melicode = data.get('melicode', '')

            if len(melicode) != 10 or not melicode.isdigit():
                return JsonResponse({
                    'exists': False,
                    'message': 'کد ملی باید 10 رقم باشد'
                })

            try:
                investor = accuntmodel.objects.get(melicode=melicode)
                return JsonResponse({
                    'exists': True,
                    'firstname': investor.firstname or '',
                    'lastname': investor.lastname or '',
                    'fullname': f"{investor.firstname or ''} {investor.lastname or ''}".strip()
                })
            except accuntmodel.DoesNotExist:
                return JsonResponse({
                    'exists': False,
                    'message': 'کد ملی در سیستم وجود ندارد. لطفا ابتدا ثبت نام کنید.'
                })
        except json.JSONDecodeError:
            return JsonResponse({'error': 'داده نامعتبر'}, status=400)

    return JsonResponse({'error': 'متد نامعتبر'}, status=400)


@csrf_exempt
def convert_amount_to_words(request):
    """تبدیل مبلغ به حروف"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            amount_str = data.get('amount', '0')

            try:
                amount_int = int(amount_str)
                if amount_int <= 0:
                    return JsonResponse({
                        'success': False,
                        'error': 'مبلغ باید بزرگتر از صفر باشد'
                    })

                words = number_to_words(amount_int)
                return JsonResponse({
                    'success': True,
                    'amount_letters': words
                })
            except ValueError:
                return JsonResponse({
                    'success': False,
                    'error': 'مبلغ نامعتبر است'
                })
        except json.JSONDecodeError:
            return JsonResponse({'error': 'داده نامعتبر'}, status=400)

    return JsonResponse({'error': 'متد نامعتبر'}, status=400)
def investment_registration(request):
    """صفحه ثبت سرمایه‌گذاری"""
    payment_accounts = Paymentnumber.objects.filter(is_active=True)

    if request.method == 'POST':
        melicode = request.POST.get('melicode', '').strip()
        investment_date = request.POST.get('investment_date')  # تاریخ شمسی
        gregorian_date = request.POST.get('gregorian_date')  # تاریخ میلادی از فیلد مخفی
        amount = request.POST.get('amount')
        payment_method = request.POST.get('payment_method')
        payment_account_id = request.POST.get('payment_account')

        # بررسی کد ملی
        if not melicode or len(melicode) != 10 or not melicode.isdigit():
            return render(request, 'cash_management/investment_registration.html', {
                'error': 'کد ملی باید 10 رقم باشد',
                'payment_accounts': payment_accounts
            })

        try:
            investor = accuntmodel.objects.get(melicode=melicode)
        except accuntmodel.DoesNotExist:
            return render(request, 'cash_management/investment_registration.html', {
                'error': 'کد ملی در سیستم وجود ندارد. لطفا ابتدا ثبت نام کنید.',
                'payment_accounts': payment_accounts
            })

        # بررسی مبلغ
        try:
            amount_int = int(amount)
            if amount_int <= 0:
                return render(request, 'cash_management/investment_registration.html', {
                    'error': 'مبلغ باید بزرگتر از صفر باشد',
                    'payment_accounts': payment_accounts
                })
        except (ValueError, TypeError):
            return render(request, 'cash_management/investment_registration.html', {
                'error': 'مبلغ نامعتبر است',
                'payment_accounts': payment_accounts
            })

        # بررسی روش پرداخت
        if payment_method == 'bank_transfer' and not payment_account_id:
            return render(request, 'cash_management/investment_registration.html', {
                'error': 'برای روش واریز به حساب، لطفاً حساب بانکی را انتخاب کنید.',
                'payment_accounts': payment_accounts
            })

        # **تبدیل تاریخ به میلادی**
        investment_date_obj = None

        # اولویت اول: استفاده از تاریخ میلادی ارسال شده از فیلد مخفی
        if gregorian_date:
            try:
                investment_date_obj = datetime.strptime(gregorian_date, '%Y-%m-%d').date()
            except ValueError:
                pass

        # اگر تاریخ میلادی معتبر نبود، تاریخ شمسی را تبدیل کنیم
        if not investment_date_obj and investment_date:
            try:
                # حذف فاصله و نرمال‌سازی تاریخ
                investment_date_clean = investment_date.strip()

                # جدا کردن بخش‌های تاریخ
                # فرض بر این است که فرمت: ۱۴۰۴/۰۹/۰۱
                parts = investment_date_clean.split('/')
                if len(parts) == 3:
                    year = int(parts[0])
                    month = int(parts[1])
                    day = int(parts[2])

                    # تبدیل تاریخ شمسی به میلادی
                    jalali_date = jdatetime.date(year, month, day)
                    gregorian_date_obj = jalali_date.togregorian()
                    investment_date_obj = gregorian_date_obj
                else:
                    return render(request, 'cash_management/investment_registration.html', {
                        'error': 'فرمت تاریخ نامعتبر است. باید به فرمت ۱۴۰۴/۰۹/۰۱ باشد.',
                        'payment_accounts': payment_accounts
                    })
            except (ValueError, IndexError, AttributeError) as e:
                return render(request, 'cash_management/investment_registration.html', {
                    'error': f'تاریخ وارد شده معتبر نیست: {str(e)}',
                    'payment_accounts': payment_accounts
                })

        if not investment_date_obj:
            return render(request, 'cash_management/investment_registration.html', {
                'error': 'تاریخ وارد نشده یا نامعتبر است',
                'payment_accounts': payment_accounts
            })

        # ایجاد رکورد سرمایه‌گذاری
        try:
            investment = Investment(
                investor=investor,
                investment_date=investment_date_obj,  # تاریخ میلادی
                amount=amount_int,
                amount_letters=number_to_words(amount_int),
                payment_method=payment_method
            )

            if payment_method == 'bank_transfer' and payment_account_id:
                payment_account = Paymentnumber.objects.get(id=payment_account_id, is_active=True)
                investment.payment_account = payment_account

            investment.save()

            # ثبت موفق
            return render(request, 'cash_management/investment_registration.html', {
                'success_message': f'سرمایه‌گذاری با موفقیت ثبت شد. تاریخ: {investment_date}',
                'payment_accounts': payment_accounts
            })

        except Exception as e:
            return render(request, 'cash_management/investment_registration.html', {
                'error': f'خطا در ثبت اطلاعات: {str(e)}',
                'payment_accounts': payment_accounts
            })

    # درخواست GET
    return render(request, 'cash_management/investment_registration.html', {
        'payment_accounts': payment_accounts
    })


# --------------------------------------------------------گزارش سرمایه گداری-------------------------------------------------
import jdatetime
from datetime import datetime, timedelta
from django.db.models import Sum, Count, Q, Min, Max
from django.shortcuts import render
from .models import Investment
from invoice_app.models import Paymentnumber


def investment_report_view(request):
    """گزارش سرمایه‌گذاری‌ها"""

    # تاریخ امروز شمسی
    today_jalali = jdatetime.date.today()

    # پارامترهای فیلتر
    payment_method = request.GET.get('payment_method', 'all')
    filter_type = request.GET.get('filter_type', 'monthly')
    account_id = request.GET.get('account_id', 'all')

    # مقادیر پیش‌فرض - سال و ماه شمسی
    try:
        year = int(request.GET.get('year', today_jalali.year))
    except:
        year = today_jalali.year

    try:
        month = int(request.GET.get('month', today_jalali.month))
    except:
        month = today_jalali.month

    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    # ایجاد کوئری پایه
    investments = Investment.objects.all().select_related(
        'investor', 'payment_account'
    ).order_by('-investment_date')

    # فیلتر بر اساس روش پرداخت
    if payment_method != 'all':
        investments = investments.filter(payment_method=payment_method)

    # فیلتر بر اساس حساب بانکی
    if account_id != 'all' and account_id:
        try:
            account_id_int = int(account_id)
            investments = investments.filter(payment_account_id=account_id_int)
        except (ValueError, TypeError):
            # اگر account_id معتبر نیست، نادیده بگیر
            pass

    # فیلتر بر اساس نوع گزارش
    if filter_type == 'monthly':
        try:
            # تبدیل سال و ماه شمسی به میلادی
            jalali_start = jdatetime.date(year, month, 1)

            # محاسبه آخر ماه شمسی
            if month == 12:
                next_month = jdatetime.date(year + 1, 1, 1)
            else:
                next_month = jdatetime.date(year, month + 1, 1)

            jalali_end = next_month - timedelta(days=1)

            gregorian_start = jalali_start.togregorian()
            gregorian_end = jalali_end.togregorian()

            investments = investments.filter(
                investment_date__gte=gregorian_start,
                investment_date__lte=gregorian_end
            )
        except Exception as e:
            # در صورت خطا، فیلتر نزنیم
            print(f"خطا در فیلتر ماهانه: {e}")

    elif filter_type == 'yearly':
        try:
            jalali_start = jdatetime.date(year, 1, 1)
            jalali_end = jdatetime.date(year, 12, 29)

            investments = investments.filter(
                investment_date__gte=jalali_start.togregorian(),
                investment_date__lte=jalali_end.togregorian()
            )
        except Exception as e:
            print(f"خطا در فیلتر سالانه: {e}")

    elif filter_type == 'custom' and start_date and end_date:
        try:
            # تبدیل تاریخ‌های شمسی به میلادی
            start_parts = start_date.split('/')
            end_parts = end_date.split('/')

            if len(start_parts) == 3 and len(end_parts) == 3:
                jalali_start = jdatetime.date(
                    int(start_parts[0]), int(start_parts[1]), int(start_parts[2])
                )
                jalali_end = jdatetime.date(
                    int(end_parts[0]), int(end_parts[1]), int(end_parts[2])
                )

                investments = investments.filter(
                    investment_date__gte=jalali_start.togregorian(),
                    investment_date__lte=jalali_end.togregorian()
                )
        except Exception as e:
            print(f"خطا در فیلتر بازه دلخواه: {e}")

    # محاسبات آماری
    total_amount = investments.aggregate(total=Sum('amount'))['total'] or 0
    investment_count = investments.count()
    average_amount = total_amount / investment_count if investment_count > 0 else 0

    # گروه‌بندی بر اساس روش پرداخت
    by_payment_method = investments.values('payment_method').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')

    # گروه‌بندی بر اساس سرمایه‌گذار
    by_investor = investments.values(
        'investor__id',
        'investor__firstname',
        'investor__lastname',
        'investor__melicode'
    ).annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')[:10]

    # گروه‌بندی بر اساس حساب بانکی
    by_payment_account = investments.values(
        'payment_account__id',
        'payment_account__name',
        'payment_account__bank_name',
        'payment_account__account_number'
    ).annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')

    # لیست حساب‌های بانکی فعال
    payment_accounts = Paymentnumber.objects.filter(is_active=True).order_by('name')

    # لیست سال‌های موجود (شمسی)
    years_jalali = []

    # روش 1: استفاده از Min و Max (بهینه)
    try:
        earliest_date = Investment.objects.aggregate(earliest=Min('investment_date'))['earliest']
        latest_date = Investment.objects.aggregate(latest=Max('investment_date'))['latest']

        if earliest_date and latest_date:
            try:
                jalali_earliest = jdatetime.date.fromgregorian(date=earliest_date)
                jalali_latest = jdatetime.date.fromgregorian(date=latest_date)

                for y in range(jalali_earliest.year, jalali_latest.year + 1):
                    years_jalali.append(y)
            except:
                years_jalali.append(today_jalali.year)
    except:
        # اگر خطا خورد، از روش جایگزین استفاده کن
        years_jalali = []
        distinct_dates = Investment.objects.dates('investment_date', 'year')
        for date in distinct_dates:
            try:
                jalali_date = jdatetime.date.fromgregorian(date=date)
                if jalali_date.year not in years_jalali:
                    years_jalali.append(jalali_date.year)
            except:
                continue

    # اگر لیست سال‌ها خالی است، سال جاری را اضافه کن
    if not years_jalali:
        years_jalali.append(today_jalali.year)

    # مرتب‌سازی نزولی
    years_jalali.sort(reverse=True)

    # اگر سال جاری در لیست نیست، اضافه کن
    if today_jalali.year not in years_jalali:
        years_jalali.insert(0, today_jalali.year)

    # نام‌های فارسی ماه‌ها
    persian_months = [
        (1, 'فروردین'), (2, 'اردیبهشت'), (3, 'خرداد'),
        (4, 'تیر'), (5, 'مرداد'), (6, 'شهریور'),
        (7, 'مهر'), (8, 'آبان'), (9, 'آذر'),
        (10, 'دی'), (11, 'بهمن'), (12, 'اسفند')
    ]

    # پیش‌پردازش سرمایه‌گذاری‌ها برای template
    investments_list = []
    for inv in investments:
        # تبدیل تاریخ به شمسی برای نمایش
        try:
            inv.jalali_date = jdatetime.date.fromgregorian(date=inv.investment_date)
            inv.jalali_date_str = inv.jalali_date.strftime('%Y/%m/%d')
        except:
            inv.jalali_date_str = str(inv.investment_date)
        investments_list.append(inv)

    # آماده‌سازی context
    context = {
        'investments': investments_list,
        'total_amount': total_amount,
        'investment_count': investment_count,
        'average_amount': average_amount,
        'by_payment_method': by_payment_method,
        'by_investor': by_investor,
        'by_payment_account': by_payment_account,
        'payment_accounts': payment_accounts,
        'years': years_jalali,
        'persian_months': persian_months,
        'payment_method': payment_method,
        'account_id': account_id,
        'filter_type': filter_type,
        'selected_year': year,
        'selected_month': month,
        'start_date': start_date,
        'end_date': end_date,
        'today_jalali': today_jalali.strftime('%Y/%m/%d'),
        'payment_methods': Investment.PAYMENT_METHOD_CHOICES,
    }

    return render(request, 'cash_management/investment_report.html', context)

# ------------------------------------------------------تایید چرداخت-----------------------------------------------------------------

from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_GET
from django.db.models import Sum, Count, Q, Min, Max
from django.db import transaction
from django.utils import timezone
from django.urls import reverse
from django.contrib.auth import get_user_model
import json
import logging
from decimal import Decimal
import jdatetime
from datetime import datetime, date, timedelta

from .forms import InvestmentForm
from .models import (
    Investment, Discrepancy, DailyCashStatus, DailyBranchCash,
    DailyCheque, DailyCredit, DailyInvestment, DailyCashAdjustment,
    CashRegister
)
from invoice_app.models import Invoicefrosh, CheckPayment, CreditPayment, Paymentnumber
from cantact_app.models import Branch, accuntmodel

User = get_user_model()
logger = logging.getLogger(__name__)


# -------------------------------------------------------------------
# توابع کمکی
# -------------------------------------------------------------------

def convert_persian_to_english(number_str):
    """تبدیل اعداد فارسی و عربی به انگلیسی"""
    if not number_str:
        return "0"

    persian_to_english = {
        '۰': '0', '٠': '0',
        '۱': '1', '١': '1',
        '۲': '2', '٢': '2',
        '۳': '3', '٣': '3',
        '۴': '4', '٤': '4',
        '۵': '5', '٥': '5',
        '۶': '6', '٦': '6',
        '۷': '7', '٧': '7',
        '۸': '8', '٨': '8',
        '۹': '9', '٩': '9',
        '٫': '.', ',': '', '٬': '', ' ': ''
    }

    result = ''
    for char in str(number_str):
        if char in persian_to_english:
            result += persian_to_english[char]
        elif char.isdigit() or char == '.':
            result += char

    return result if result else "0"


def get_date_status(gregorian_date):
    """بررسی وضعیت تایید یک روز"""
    try:
        daily_status = DailyCashStatus.objects.get(date=gregorian_date)

        # بررسی وضعیت شعبه‌ها
        branch_cashes = DailyBranchCash.objects.filter(daily_status=daily_status)
        if branch_cashes.filter(is_verified=False).exists():
            return 'pending'

        # بررسی وضعیت چک‌ها
        cheques = DailyCheque.objects.filter(daily_status=daily_status)
        if cheques.exists() and cheques.filter(is_verified=False).exists():
            return 'pending'

        # بررسی وضعیت نسیه‌ها
        credits = DailyCredit.objects.filter(daily_status=daily_status)
        if credits.exists() and credits.filter(is_verified=False).exists():
            return 'pending'

        # بررسی وضعیت سرمایه‌گذاری‌ها
        investments = DailyInvestment.objects.filter(daily_status=daily_status)
        if investments.exists() and investments.filter(is_verified=False).exists():
            return 'pending'

        # اگر همه آیتم‌ها تایید شده‌اند یا وجود ندارند
        return 'verified'

    except DailyCashStatus.DoesNotExist:
        # اگر وضعیت روز وجود ندارد، بررسی می‌کنیم آیا فعالیتی برای این روز هست؟

        # بررسی فعالیت شعبه‌ها
        has_branch_activity = Invoicefrosh.objects.filter(
            created_at__date=gregorian_date
        ).exists()

        # بررسی سرمایه‌گذاری
        has_investment = Investment.objects.filter(
            investment_date=gregorian_date
        ).exists()

        # بررسی چک‌های سررسید
        has_cheque = CheckPayment.objects.filter(
            check_date=gregorian_date
        ).exists()

        # بررسی نسیه‌های سررسید
        has_credit = CreditPayment.objects.filter(
            due_date=gregorian_date
        ).exists()

        # اگر هیچ فعالیتی وجود ندارد، وضعیت خالی است
        if not (has_branch_activity or has_investment or has_cheque or has_credit):
            return 'empty'

        # اگر فعالیت وجود دارد اما وضعیت روز ایجاد نشده، در انتظار است
        return 'pending'


def create_fake_invoice(branch, date, amount, payment_method, user=None, request=None):
    """ایجاد فاکتور فیک با تمام الزامات"""
    try:
        if not branch:
            logger.error("شعبه برای ایجاد فاکتور فیک مشخص نشده است")
            return None

        # تعیین کاربر
        if user is None and request is not None:
            user = request.user
        elif user is None:
            logger.error("کاربر برای ایجاد فاکتور فیک مشخص نشده است")
            return None

        # تبدیل مبلغ به integer
        amount_int = int(Decimal(str(amount)))

        # محاسبه قیمت معیار
        standard_price = int((amount_int / 17) * 10)

        # محاسبه سود
        profit_amount = amount_int - standard_price

        # ایمپورت مدل‌های مورد نیاز
        from invoice_app.models import Invoicefrosh, InvoiceItemfrosh, POSDevice
        from account_app.models import InventoryCount

        # 1. بررسی و ایجاد کالای "سیستم" در InventoryCount
        try:
            system_product = InventoryCount.objects.get(
                product_name='سیستم',
                branch=branch
            )
            logger.info(f"کالای سیستم برای شعبه {branch.name} یافت شد")

        except InventoryCount.DoesNotExist:
            system_product = InventoryCount.objects.create(
                product_name='سیستم',
                branch=branch,
                counter=user,
                quantity=0,
                selling_price=amount_int,
                profit_percentage=Decimal('70.00'),
                is_new=True,
            )
            logger.info(f"کالای سیستم جدید برای شعبه {branch.name} ایجاد شد")

        # 2. ایجاد فاکتور فیک
        from django.utils import timezone
        from datetime import datetime

        # ساخت تاریخ و زمان
        invoice_datetime = timezone.make_aware(datetime.combine(date, datetime.min.time()))

        # یافتن دستگاه پوز پیشفرض
        pos_device = None
        if payment_method == 'pos':
            try:
                pos_device = POSDevice.objects.get(is_default=True, is_active=True)
            except POSDevice.DoesNotExist:
                logger.warning("هیچ دستگاه پوز پیشفرض فعالی یافت نشد")

        # ساخت serial_number
        import time
        timestamp = int(time.time())
        serial_number = f"FAKE-{payment_method.upper()}-{date.strftime('%Y%m%d')}-{branch.id}-{timestamp}"

        # ایجاد فاکتور
        invoice = Invoicefrosh.objects.create(
            branch=branch,
            created_by=user,
            created_at=invoice_datetime,
            payment_date=invoice_datetime if payment_method == 'cash' else None,
            payment_method=payment_method,
            pos_device=pos_device,
            total_amount=amount_int,
            total_without_discount=amount_int,
            discount=0,
            is_finalized=True,
            is_paid=True,
            customer_name=f'سیستم - {payment_method} - گردش مالی',
            customer_phone='',
            serial_number=serial_number,
            paid_amount=amount_int,
            total_standard_price=standard_price,
            total_profit=profit_amount
        )

        # 3. ایجاد آیتم فاکتور
        InvoiceItemfrosh.objects.create(
            invoice=invoice,
            product=system_product,
            quantity=1,
            price=amount_int,
            total_price=amount_int,
            standard_price=standard_price,
            discount=0
        )

        logger.info(f"✅ فاکتور فیک ایجاد شد: {invoice.id}")
        return invoice

    except Exception as e:
        logger.error(f"❌ خطا در ایجاد فاکتور فیک: {str(e)}", exc_info=True)
        return None


def create_discrepancy(item_type, item_id, previous_amount, new_amount, reason, request, branch=None):
    """ایجاد رکورد مغایرت"""
    try:
        item = None
        description = ""

        if item_type == 'branch_cash':
            item = DailyBranchCash.objects.get(id=item_id)
            branch = item.branch
            description = f"تغییر مبلغ شعبه {branch.name}"
        elif item_type == 'cheque':
            item = DailyCheque.objects.get(id=item_id)
            branch = item.branch
            description = f"تغییر مبلغ چک {item.cheque_number}"
        elif item_type == 'credit':
            item = DailyCredit.objects.get(id=item_id)
            branch = item.branch
            description = f"تغییر مبلغ نسیه {item.customer_name}"
        elif item_type == 'investment':
            item = DailyInvestment.objects.get(id=item_id)
            description = f"تغییر مبلغ سرمایه‌گذاری {item.investor_name}"
        else:
            return None

        discrepancy = Discrepancy.objects.create(
            discrepancy_date=item.daily_status.date,
            branch=branch,
            previous_amount=previous_amount,
            new_amount=new_amount,
            difference=new_amount - previous_amount,
            item_type=item_type,
            item_id=item_id,
            description=description,
            reason=reason,
            reviewer_melicode=request.user.username,
            responder_melicode=request.user.username,
            created_by=request.user,
            review_status='pending',
            resolution_status='unresolved'
        )

        return discrepancy
    except Exception as e:
        logger.error(f"خطا در ایجاد مغایرت: {str(e)}")
        return None


# -------------------------------------------------------------------
# توابع مربوط به سرمایه‌گذاری
# -------------------------------------------------------------------

@csrf_exempt
def check_melicode(request):
    """بررسی وجود کد ملی در دیتابیس"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            melicode = data.get('melicode', '')

            if len(melicode) != 10 or not melicode.isdigit():
                return JsonResponse({
                    'exists': False,
                    'message': 'کد ملی باید 10 رقم باشد'
                })

            try:
                investor = accuntmodel.objects.get(melicode=melicode)
                return JsonResponse({
                    'exists': True,
                    'firstname': investor.firstname or '',
                    'lastname': investor.lastname or '',
                    'fullname': f"{investor.firstname or ''} {investor.lastname or ''}".strip()
                })
            except accuntmodel.DoesNotExist:
                return JsonResponse({
                    'exists': False,
                    'message': 'کد ملی در سیستم وجود ندارد. لطفا ابتدا ثبت نام کنید.'
                })
        except json.JSONDecodeError:
            return JsonResponse({'error': 'داده نامعتبر'}, status=400)

    return JsonResponse({'error': 'متد نامعتبر'}, status=400)


@csrf_exempt
def convert_amount_to_words(request):
    """تبدیل مبلغ به حروف"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            amount_str = data.get('amount', '0')

            try:
                amount_int = int(amount_str)
                if amount_int <= 0:
                    return JsonResponse({
                        'success': False,
                        'error': 'مبلغ باید بزرگتر از صفر باشد'
                    })

                words = number_to_words(amount_int)
                return JsonResponse({
                    'success': True,
                    'amount_letters': words
                })
            except ValueError:
                return JsonResponse({
                    'success': False,
                    'error': 'مبلغ نامعتبر است'
                })
        except json.JSONDecodeError:
            return JsonResponse({'error': 'داده نامعتبر'}, status=400)

    return JsonResponse({'error': 'متد نامعتبر'}, status=400)

# -------------------------------------------------------------------
# توابع تقویم و مدیریت روزانه
# -------------------------------------------------------------------

@login_required
def calendar_view(request):
    """نمایش تقویم"""
    today = jdatetime.datetime.now()

    try:
        year = int(request.GET.get('year', today.year))
        month = int(request.GET.get('month', today.month))
    except:
        year, month = today.year, today.month

    month = max(1, min(12, month))

    month_names = [
        'فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
        'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند'
    ]

    # محاسبه تعداد روزهای ماه
    if month <= 6:
        days_in_month = 31
    elif month <= 11:
        days_in_month = 30
    else:
        first_day = jdatetime.datetime(year, 12, 1)
        days_in_month = 30 if first_day.isleap() else 29

    # محاسبه اولین روز هفته
    first_day_obj = jdatetime.datetime(year, month, 1)
    first_weekday = (first_day_obj.weekday() + 2) % 7

    # ایجاد تقویم
    calendar_weeks = []
    day_counter = 0

    for week in range(6):
        week_days = []

        for weekday in range(7):
            if (week == 0 and weekday < first_weekday) or day_counter >= days_in_month:
                day_data = {'day': None, 'status': 'empty'}
            else:
                day_number = day_counter + 1
                jdate = jdatetime.datetime(year, month, day_number)
                gregorian_date = jdate.togregorian().date()

                # دریافت وضعیت روز
                status = get_date_status(gregorian_date)

                is_today = (year == today.year and month == today.month and day_number == today.day)

                day_data = {
                    'day': day_number,
                    'year': year,
                    'month': month,
                    'jalali_date': f"{year}/{month}/{day_number}",
                    'gregorian_date': gregorian_date,
                    'is_current_month': True,
                    'is_today': is_today,
                    'status': status
                }
                day_counter += 1

            week_days.append(day_data)

        calendar_weeks.append(week_days)

    context = {
        'calendar_data': calendar_weeks,
        'current_year': year,
        'current_month': month,
        'current_month_name': month_names[month - 1],
        'year_range': range(year - 5, year + 6),
    }

    return render(request, 'cash_management/calendar.html', context)


def create_branch_records_for_day(daily_status, branches):
    """ایجاد رکوردهای پیش‌فرض برای شعبه‌ها در یک روز"""
    for branch in branches:
        # بررسی وجود رکورد برای این شعبه و روز
        existing_cash = DailyBranchCash.objects.filter(
            daily_status=daily_status,
            branch=branch
        ).exists()

        if not existing_cash:
            DailyBranchCash.objects.create(
                daily_status=daily_status,
                branch=branch,
                cash_amount=Decimal('0'),
                pos_amount=Decimal('0'),
                is_verified=False,
                created_by=daily_status.created_by if hasattr(daily_status, 'created_by') else None
            )


@login_required
def day_detail_view(request):
    """نمایش جزئیات روز - نسخه دیباگ"""
    date_str = request.GET.get('date', '')

    if not date_str:
        today = jdatetime.datetime.now()
        date_str = f"{today.year}-{today.month}-{today.day}"

    try:
        # تبدیل تاریخ
        parts = date_str.split('-')
        year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
        jdate = jdatetime.datetime(year, month, day)
        gregorian_date = jdate.togregorian().date()
        jalali_date = f"{year}/{month}/{day}"

        logger.info(f"دریافت درخواست برای تاریخ: {date_str} -> {gregorian_date}")

        # 1. ایجاد یا دریافت وضعیت روز
        daily_status, created = DailyCashStatus.objects.get_or_create(
            date=gregorian_date,
            defaults={'is_verified': False}
        )

        # 2. دریافت شعبه‌ها
        branches = Branch.objects.all()
        logger.info(f"تعداد شعبه‌ها: {branches.count()}")

        # 3. ساخت لیست شعبه‌ها با اطلاعات کامل
        branch_data = []

        for branch in branches:
            logger.info(f"پردازش شعبه: {branch.name}")

            # دریافت یا ایجاد رکورد روزانه شعبه
            branch_cash, _ = DailyBranchCash.objects.get_or_create(
                daily_status=daily_status,
                branch=branch,
                defaults={
                    'cash_amount': Decimal('0'),
                    'pos_amount': Decimal('0'),
                    'is_verified': False
                }
            )

            # 4. **دیباگ: بررسی فاکتورهای این شعبه و تاریخ**
            # ابتدا ببینیم چند فاکتور برای این تاریخ و شعبه وجود دارد
            all_invoices = Invoicefrosh.objects.filter(
                branch=branch,
                created_at__date=gregorian_date
            )

            logger.info(f"شعبه {branch.name}: کل فاکتورها = {all_invoices.count()}")

            # فاکتورهای نقدی
            cash_invoices = all_invoices.filter(payment_method='cash')
            cash_total = cash_invoices.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')

            logger.info(f"شعبه {branch.name}: فاکتورهای نقدی = {cash_invoices.count()}, مجموع = {cash_total}")

            # فاکتورهای پوز
            pos_invoices = all_invoices.filter(payment_method='pos')
            logger.info(f"شعبه {branch.name}: فاکتورهای پوز = {pos_invoices.count()}")

            # نمایش جزئیات هر فاکتور پوز
            for inv in pos_invoices:
                logger.info(f"  فاکتور پوز #{inv.id}: مبلغ={inv.total_amount}, "
                            f"دستگاه={inv.pos_device.device_name if inv.pos_device else 'بدون دستگاه'}, "
                            f"وضعیت final={inv.is_finalized}, وضعیت paid={inv.is_paid}")

            pos_total = pos_invoices.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')

            # تفکیک دستگاه‌های پوز
            pos_details = []
            device_groups = {}

            for invoice in pos_invoices:
                device_name = invoice.pos_device.device_name if invoice.pos_device else 'نامشخص'
                bank_name = invoice.pos_device.bank_name if invoice.pos_device else 'نامشخص'
                device_key = f"{device_name}_{bank_name}"

                if device_key in device_groups:
                    device_groups[device_key]['amount'] += invoice.total_amount
                    device_groups[device_key]['count'] += 1
                else:
                    device_groups[device_key] = {
                        'device_name': device_name,
                        'bank_name': bank_name,
                        'amount': invoice.total_amount,
                        'count': 1
                    }

            # تبدیل دیکشنری به لیست
            for device_key, info in device_groups.items():
                pos_details.append(info)

            # اگر کاربر مقداری وارد نکرده، از فاکتورها استفاده کن
            if branch_cash.cash_amount == 0 and cash_total > 0:
                branch_cash.cash_amount = cash_total

            if branch_cash.pos_amount == 0 and pos_total > 0:
                branch_cash.pos_amount = pos_total

            branch_cash.save()

            # آماده‌سازی داده‌ها
            branch_data.append({
                'branch': branch,
                'branch_cash': branch_cash,
                'cash_total': cash_total,
                'pos_total': pos_total,
                'pos_details': pos_details,
                'cash_invoice_count': cash_invoices.count(),
                'pos_invoice_count': pos_invoices.count(),
                'total_invoices': cash_invoices.count() + pos_invoices.count()
            })

        # 5. **لاگ نهایی**
        total_cash = sum(item['cash_total'] for item in branch_data)
        total_pos = sum(item['pos_total'] for item in branch_data)

        logger.info(f"نتایج نهایی: مجموع نقدی = {total_cash}, مجموع پوز = {total_pos}")

        # 6. بقیه کدهای شما...
        # [بقیه کدهای شما بدون تغییر]

        context = {
            'jalali_date': jalali_date,
            'date_str': date_str,
            'gregorian_date': gregorian_date,
            'daily_status': daily_status,
            'branch_data': branch_data,
            'total_cash': total_cash,
            'total_pos': total_pos,
            'total_all': float(total_cash) + float(total_pos),
            # ... بقیه متغیرها
        }

        return render(request, 'cash_management/day_detail.html', context)

    except Exception as e:
        logger.error(f"خطا در نمایش جزئیات روز: {str(e)}", exc_info=True)
        return render(request, 'cash_management/error.html', {
            'error': f'خطا در نمایش جزئیات: {str(e)}',
            'date_str': date_str
        })

# -------------------------------------------------------------------
# توابع AJAX برای ذخیره داده‌ها
# -------------------------------------------------------------------

@login_required
@require_POST
@csrf_exempt
def save_branch_cash(request):
    """ذخیره مبالغ نقدی و پوز شعبه"""
    try:
        data = json.loads(request.body)
        logger.debug(f"داده‌های دریافتی: {data}")

        date_str = data.get('date')
        branch_id = data.get('branch_id')
        cash_amount_str = data.get('cash_amount', '0')
        pos_amount_str = data.get('pos_amount', '0')

        # تبدیل اعداد فارسی به انگلیسی
        cash_amount = convert_persian_to_english(cash_amount_str)
        pos_amount = convert_persian_to_english(pos_amount_str)

        if not branch_id:
            return JsonResponse({
                'success': False,
                'error': 'شناسه شعبه ارسال نشده است'
            })

        try:
            branch_id_int = int(branch_id)
        except (ValueError, TypeError) as e:
            logger.error(f"خطا در تبدیل branch_id به عدد: {branch_id} - {e}")
            return JsonResponse({
                'success': False,
                'error': f'شناسه شعبه نامعتبر است: {branch_id}'
            })

        # تبدیل تاریخ
        try:
            parts = date_str.split('-')
            year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
            jdate = jdatetime.datetime(year, month, day)
            gregorian_date = jdate.togregorian().date()
        except Exception as e:
            logger.error(f"خطا در تبدیل تاریخ: {date_str} - {e}")
            return JsonResponse({
                'success': False,
                'error': f'تاریخ نامعتبر است: {date_str}'
            })

        # دریافت یا ایجاد وضعیت روز
        daily_status, created = DailyCashStatus.objects.get_or_create(
            date=gregorian_date,
            defaults={'is_verified': False}
        )

        if created:
            daily_status.created_by = request.user
            daily_status.save()

        # دریافت شعبه
        try:
            branch = Branch.objects.get(id=branch_id_int)
        except Branch.DoesNotExist:
            logger.error(f"شعبه با شناسه {branch_id_int} یافت نشد")
            return JsonResponse({
                'success': False,
                'error': f'شعبه با شناسه {branch_id_int} یافت نشد'
            })

        # دریافت یا ایجاد رکورد شعبه
        branch_cash, created = DailyBranchCash.objects.get_or_create(
            daily_status=daily_status,
            branch=branch,
            defaults={
                'cash_amount': Decimal('0'),
                'pos_amount': Decimal('0'),
                'created_by': request.user
            }
        )

        # ذخیره مقادیر قبلی
        previous_cash = branch_cash.cash_amount
        previous_pos = branch_cash.pos_amount
        was_verified = branch_cash.is_verified

        new_cash = Decimal(cash_amount)
        new_pos = Decimal(pos_amount)

        with transaction.atomic():
            # بررسی تغییرات و ایجاد فاکتور فیک
            # برای نقدی: اگر مقدار جدید بزرگتر از صفر است فاکتور فیک ایجاد کن
            if new_cash > 0:
                # برای نقدی: همیشه فاکتور ایجاد کن (مگر اینکه قبلاً هم فاکتور ساخته باشیم)
                # ما اینجا ساده فرض می‌کنیم که همیشه فاکتور ایجاد می‌شود
                create_fake_invoice(
                    branch=branch,
                    date=gregorian_date,
                    amount=new_cash,
                    payment_method='cash',
                    user=request.user
                )

            # برای پوز: اگر مقدار جدید بزرگتر از صفر است فاکتور فیک ایجاد کن
            if new_pos > 0:
                create_fake_invoice(
                    branch=branch,
                    date=gregorian_date,
                    amount=new_pos,
                    payment_method='pos',
                    user=request.user
                )

            # به‌روزرسانی رکورد شعبه
            branch_cash.cash_amount = new_cash
            branch_cash.pos_amount = new_pos
            branch_cash.updated_at = timezone.now()
            branch_cash.save()

            # ثبت مغایرت اگر آیتم قبلاً تایید شده بود
            if was_verified:
                if previous_cash != new_cash:
                    create_discrepancy(
                        item_type='branch_cash',
                        item_id=branch_cash.id,
                        previous_amount=previous_cash,
                        new_amount=new_cash,
                        reason=f"تغییر مبلغ نقدی شعبه {branch.name} از {previous_cash} به {new_cash}",
                        request=request,
                        branch=branch
                    )

                if previous_pos != new_pos:
                    create_discrepancy(
                        item_type='branch_cash',
                        item_id=branch_cash.id,
                        previous_amount=previous_pos,
                        new_amount=new_pos,
                        reason=f"تغییر مبلغ پوز شعبه {branch.name} از {previous_pos} به {new_pos}",
                        request=request,
                        branch=branch
                    )

        return JsonResponse({
            'success': True,
            'message': 'مبلغ با موفقیت ذخیره شد'
        })

    except Exception as e:
        logger.error(f"خطا در ذخیره مبلغ شعبه: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'خطای سیستمی: {str(e)}'
        })@login_required
@require_POST
@csrf_exempt
def save_cheque(request):
    """ذخیره وضعیت چک"""
    try:
        data = json.loads(request.body)

        cheque_id = data.get('cheque_id')
        status = data.get('status')
        destination_account = data.get('destination_account', '')

        cheque = DailyCheque.objects.get(id=cheque_id)

        # ذخیره مقدار قبلی برای بررسی مغایرت
        previous_amount = cheque.cheque_amount
        was_verified = cheque.is_verified

        cheque.status = status

        if status == 'passed':
            cheque.destination_account = destination_account
            cheque.passed_date = timezone.now().date()

        cheque.save()

        # اگر چک قبلاً تایید شده بود و وضعیت تغییر کرده، ایجاد مغایرت
        if was_verified and cheque.status != 'passed':
            create_discrepancy(
                item_type='cheque',
                item_id=cheque_id,
                previous_amount=previous_amount,
                new_amount=cheque.cheque_amount,
                reason=f"تغییر وضعیت چک {cheque.cheque_number} از 'پاس شده' به '{cheque.status}'",
                request=request,
                branch=cheque.branch
            )

        return JsonResponse({
            'success': True,
            'message': 'وضعیت چک به‌روز شد'
        })

    except Exception as e:
        logger.error(f"خطا در ذخیره وضعیت چک: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@require_POST
@csrf_exempt
def save_credit(request):
    """ذخیره وضعیت نسیه"""
    try:
        data = json.loads(request.body)

        credit_id = data.get('credit_id')
        status = data.get('status')
        payment_method = data.get('payment_method', '')

        credit = DailyCredit.objects.get(id=credit_id)

        # ذخیره مقدار قبلی برای بررسی مغایرت
        previous_amount = credit.credit_amount
        was_verified = credit.is_verified

        credit.status = status

        if status == 'paid':
            credit.payment_method = payment_method
            credit.paid_date = timezone.now().date()

        credit.save()

        # اگر نسیه قبلاً تایید شده بود و وضعیت تغییر کرده، ایجاد مغایرت
        if was_verified and credit.status != 'paid':
            create_discrepancy(
                item_type='credit',
                item_id=credit_id,
                previous_amount=previous_amount,
                new_amount=credit.credit_amount,
                reason=f"تغییر وضعیت نسیه {credit.customer_name} از 'پرداخت شده' به '{credit.status}'",
                request=request,
                branch=credit.branch
            )

        return JsonResponse({
            'success': True,
            'message': 'وضعیت نسیه به‌روز شد'
        })

    except Exception as e:
        logger.error(f"خطا در ذخیره وضعیت نسیه: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@require_POST
@csrf_exempt
def save_investment(request):
    """ذخیره اطلاعات سرمایه‌گذاری"""
    try:
        data = json.loads(request.body)

        investment_id = data.get('investment_id')
        amount_str = data.get('amount', '0')
        payment_method = data.get('payment_method')
        destination_account = data.get('destination_account', '')

        amount = convert_persian_to_english(amount_str)

        investment = DailyInvestment.objects.get(id=investment_id)

        # ذخیره مقدار قبلی برای بررسی مغایرت
        previous_amount = investment.investment_amount
        was_verified = investment.is_verified

        investment.investment_amount = Decimal(amount)
        investment.payment_method = payment_method
        investment.destination_account = destination_account
        investment.save()

        # اگر سرمایه‌گذاری قبلاً تایید شده بود و مقدار تغییر کرده، ایجاد مغایرت
        if was_verified and previous_amount != Decimal(amount):
            create_discrepancy(
                item_type='investment',
                item_id=investment_id,
                previous_amount=previous_amount,
                new_amount=Decimal(amount),
                reason=f"تغییر مبلغ سرمایه‌گذاری {investment.investor_name} از {previous_amount} به {amount}",
                request=request
            )

        return JsonResponse({
            'success': True,
            'message': 'اطلاعات سرمایه‌گذاری به‌روز شد'
        })

    except Exception as e:
        logger.error(f"خطا در ذخیره سرمایه‌گذاری: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


# -------------------------------------------------------------------
# توابع تایید و ثبت نهایی
# -------------------------------------------------------------------

@login_required
@require_POST
@csrf_exempt
def verify_item(request):
    """تایید یک آیتم - نسخه اصلاح شده"""
    try:
        data = json.loads(request.body)
        logger.info(f"verify_item دریافت داده: {data}")

        item_type = data.get('item_type')
        item_id = data.get('item_id')

        # دریافت آیتم
        if item_type == 'branch_cash':
            item = DailyBranchCash.objects.get(id=item_id)
            item_name = f"شعبه {item.branch.name}"

            # بررسی آیا آیتم مقدار غیرصفر دارد؟
            cash_amount = item.cash_amount if item.cash_amount else Decimal('0')
            pos_amount = item.pos_amount if item.pos_amount else Decimal('0')
            has_amount = cash_amount > 0 or pos_amount > 0

        elif item_type == 'cheque':
            item = DailyCheque.objects.get(id=item_id)
            item_name = f"چک {item.cheque_number}"
            has_amount = item.cheque_amount > 0 and item.status == 'passed'

        elif item_type == 'credit':
            item = DailyCredit.objects.get(id=item_id)
            item_name = f"نسیه {item.customer_name}"
            has_amount = item.credit_amount > 0 and item.status == 'paid'

        elif item_type == 'investment':
            item = DailyInvestment.objects.get(id=item_id)
            item_name = f"سرمایه‌گذاری {item.investor_name}"
            has_amount = item.investment_amount > 0

        else:
            return JsonResponse({
                'success': False,
                'error': 'نوع آیتم نامعتبر'
            })

        # اگر آیتم مقدار صفر دارد، تایید معنی ندارد
        if not has_amount:
            return JsonResponse({
                'success': False,
                'error': 'آیتم‌های با مبلغ صفر نیازی به تایید ندارند'
            })

        # تغییر وضعیت تایید
        item.is_verified = not item.is_verified

        if item.is_verified:
            item.verified_by = request.user
            item.verified_at = timezone.now()
        else:
            item.verified_by = None
            item.verified_at = None

        item.save()

        # پاسخ JSON
        response_data = {
            'success': True,
            'message': 'آیتم با موفقیت تایید شد' if item.is_verified else 'تایید آیتم لغو شد',
            'is_verified': item.is_verified,
        }

        # اگر تایید شده، اطلاعات آیتم را هم بفرست
        if item.is_verified:
            # برای شعبه، باید دو آیتم جداگانه بفرستیم (نقدی و پوز)
            if item_type == 'branch_cash':
                items_info = []
                cash_amount = item.cash_amount if item.cash_amount else Decimal('0')
                pos_amount = item.pos_amount if item.pos_amount else Decimal('0')

                if cash_amount > 0:
                    items_info.append({
                        'type': 'branch_cash',
                        'id': item_id,
                        'name': f"{item.branch.name} - نقدی",
                        'amount': float(cash_amount),
                        'account': None
                    })

                if pos_amount > 0:
                    items_info.append({
                        'type': 'branch_cash',
                        'id': item_id,
                        'name': f"{item.branch.name} - پوز",
                        'amount': float(pos_amount),
                        'account': None
                    })

                response_data['items_info'] = items_info
            else:
                item_amount = None
                if item_type == 'cheque':
                    item_amount = item.cheque_amount
                elif item_type == 'credit':
                    item_amount = item.credit_amount
                elif item_type == 'investment':
                    item_amount = item.investment_amount

                if item_amount and item_amount > 0:
                    response_data['item_info'] = {
                        'type': item_type,
                        'id': item_id,
                        'name': item_name,
                        'amount': float(item_amount),
                        'account': getattr(item, 'destination_account', None) or
                                   getattr(item, 'payment_method', None)
                    }

        logger.info(f"verify_item پاسخ: {response_data}")
        return JsonResponse(response_data)

    except Exception as e:
        logger.error(f"خطا در تایید آیتم: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        })@login_required


@require_POST
@csrf_exempt
def finalize_day(request):
    """تایید نهایی روز و ثبت در صندوق"""
    try:
        data = json.loads(request.body)
        date_str = data.get('date')

        # تبدیل تاریخ
        parts = date_str.split('-')
        year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
        jdate = jdatetime.datetime(year, month, day)
        gregorian_date = jdate.togregorian().date()

        # دریافت وضعیت روز
        daily_status = DailyCashStatus.objects.get(date=gregorian_date)

        # دریافت داده‌ها
        branch_cashes = DailyBranchCash.objects.filter(daily_status=daily_status, is_verified=True)
        investments = DailyInvestment.objects.filter(daily_status=daily_status, is_verified=True)
        cheques = DailyCheque.objects.filter(daily_status=daily_status, is_verified=True, status='passed')
        credits = DailyCredit.objects.filter(daily_status=daily_status, is_verified=True, status='paid')

        with transaction.atomic():
            # ابتدا رکوردهای CashRegister موجود برای این تاریخ را حذف می‌کنیم تا از تکراری شدن جلوگیری شود
            CashRegister.objects.filter(date=gregorian_date).delete()

            # برای هر شعبه یک رکورد CashRegister ایجاد می‌کنیم
            branches = Branch.objects.all()

            # جمع‌آوری اطلاعات شعبه‌ها
            for branch in branches:
                # جمع‌آوری مبالغ این شعبه
                cash_amount = Decimal('0')
                pos_amount = Decimal('0')
                cheque_amount = Decimal('0')
                credit_amount = Decimal('0')

                # مبالغ نقدی و پوز این شعبه
                branch_cash = branch_cashes.filter(branch=branch).first()
                if branch_cash:
                    cash_amount = branch_cash.cash_amount
                    pos_amount = branch_cash.pos_amount

                # چک‌های این شعبه
                branch_cheques = cheques.filter(branch=branch)
                for cheque in branch_cheques:
                    cheque_amount += cheque.cheque_amount

                # نسیه‌های این شعبه
                branch_credits = credits.filter(branch=branch)
                for credit in branch_credits:
                    credit_amount += credit.credit_amount

                # ایجاد رکورد CashRegister برای شعبه فقط اگر حداقل یک مبلغ غیرصفر باشد
                if cash_amount > 0 or pos_amount > 0 or cheque_amount > 0 or credit_amount > 0:
                    CashRegister.objects.create(
                        branch=branch,
                        date=gregorian_date,
                        cash_amount=cash_amount,
                        pos_amount=pos_amount,
                        cheque_amount=cheque_amount,
                        credit_amount=credit_amount,
                        investment_amount=Decimal('0'),  # سرمایه‌گذاری‌ها جداگانه ثبت می‌شوند
                        cheque_status='passed' if cheque_amount > 0 else 'pending',
                        credit_status='paid' if credit_amount > 0 else 'pending',
                        investment_returned=False,
                        is_verified=True,
                        verified_by=request.user,
                        verified_at=timezone.now(),
                        created_by=request.user
                    )

            # سرمایه‌گذاری‌ها (بدون شعبه)
            if investments.exists():
                total_investment = sum(inv.investment_amount for inv in investments)
                CashRegister.objects.create(
                    branch=None,  # سرمایه‌گذاری‌ها شعبه خاصی ندارند
                    date=gregorian_date,
                    cash_amount=Decimal('0'),
                    pos_amount=Decimal('0'),
                    cheque_amount=Decimal('0'),
                    credit_amount=Decimal('0'),
                    investment_amount=total_investment,
                    cheque_status='pending',
                    credit_status='pending',
                    investment_returned=False,
                    is_verified=True,
                    verified_by=request.user,
                    verified_at=timezone.now(),
                    created_by=request.user
                )

            # تایید روز
            daily_status.is_verified = True
            daily_status.verified_by = request.user
            daily_status.verified_at = timezone.now()
            daily_status.save()

        return JsonResponse({
            'success': True,
            'message': 'روز با موفقیت تایید و در صندوق ثبت شد',
            'redirect_url': reverse('cash_management:calendar')
        })

    except Exception as e:
        logger.error(f"خطا در تایید نهایی روز: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        })
# -------------------------------------------------------------------
# توابع تنظیمات و مغایرت
# -------------------------------------------------------------------

@login_required
@require_POST
@csrf_exempt
def add_adjustment(request):
    """افزودن تنظیم دستی"""
    try:
        data = json.loads(request.body)

        date_str = data.get('date')
        adjustment_type = data.get('type')
        description = data.get('description')
        amount_str = data.get('amount', '0')
        is_positive = data.get('is_positive', True)

        amount = convert_persian_to_english(amount_str)

        # تبدیل تاریخ
        parts = date_str.split('-')
        year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
        jdate = jdatetime.datetime(year, month, day)
        gregorian_date = jdate.togregorian().date()

        # دریافت وضعیت روز
        daily_status = DailyCashStatus.objects.get(date=gregorian_date)

        # ایجاد تنظیم
        DailyCashAdjustment.objects.create(
            daily_status=daily_status,
            adjustment_type=adjustment_type,
            description=description,
            amount=Decimal(amount),
            is_positive=is_positive,
            created_by=request.user
        )

        return JsonResponse({
            'success': True,
            'message': 'تنظیم با موفقیت افزوده شد'
        })

    except Exception as e:
        logger.error(f"خطا در افزودن تنظیم: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@require_POST
@csrf_exempt
def bulk_update(request):
    """به‌روزرسانی گروهی"""
    try:
        data = json.loads(request.body)
        date_str = data.get('date')
        updates = data.get('updates', [])

        # تبدیل تاریخ
        parts = date_str.split('-')
        year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
        jdate = jdatetime.datetime(year, month, day)
        gregorian_date = jdate.togregorian().date()

        daily_status = DailyCashStatus.objects.get(date=gregorian_date)

        with transaction.atomic():
            for update in updates:
                item_type = update.get('type')
                item_id = update.get('id')
                field = update.get('field')
                value = update.get('value')

                if item_type == 'branch_cash':
                    item = DailyBranchCash.objects.get(id=item_id, daily_status=daily_status)
                    if field == 'cash_amount':
                        previous_amount = item.cash_amount
                        item.cash_amount = Decimal(convert_persian_to_english(value))
                        if item.is_verified and previous_amount != item.cash_amount:
                            create_discrepancy(
                                item_type='branch_cash',
                                item_id=item_id,
                                previous_amount=previous_amount,
                                new_amount=item.cash_amount,
                                reason=f"تغییر گروهی مبلغ نقدی",
                                request=request
                            )
                    elif field == 'pos_amount':
                        previous_amount = item.pos_amount
                        item.pos_amount = Decimal(convert_persian_to_english(value))
                        if item.is_verified and previous_amount != item.pos_amount:
                            create_discrepancy(
                                item_type='branch_cash',
                                item_id=item_id,
                                previous_amount=previous_amount,
                                new_amount=item.pos_amount,
                                reason=f"تغییر گروهی مبلغ پوز",
                                request=request
                            )
                    item.save()

                elif item_type == 'investment':
                    item = DailyInvestment.objects.get(id=item_id, daily_status=daily_status)
                    if field == 'amount':
                        previous_amount = item.investment_amount
                        item.investment_amount = Decimal(convert_persian_to_english(value))
                        if item.is_verified and previous_amount != item.investment_amount:
                            create_discrepancy(
                                item_type='investment',
                                item_id=item_id,
                                previous_amount=previous_amount,
                                new_amount=item.investment_amount,
                                reason=f"تغییر گروهی مبلغ سرمایه‌گذاری",
                                request=request
                            )
                    elif field == 'payment_method':
                        item.payment_method = value
                    elif field == 'destination_account':
                        item.destination_account = value
                    item.save()

        return JsonResponse({
            'success': True,
            'message': 'به‌روزرسانی گروهی انجام شد'
        })

    except Exception as e:
        logger.error(f"خطا در به‌روزرسانی گروهی: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@require_GET
def get_discrepancies(request):
    """دریافت لیست مغایرت‌ها"""
    date_str = request.GET.get('date', '')

    if not date_str:
        return JsonResponse({'success': False, 'error': 'تاریخ مشخص نشده'})

    try:
        parts = date_str.split('-')
        year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
        jdate = jdatetime.datetime(year, month, day)
        gregorian_date = jdate.togregorian().date()

        discrepancies = Discrepancy.objects.filter(
            discrepancy_date=gregorian_date
        ).order_by('-created_at')

        data = []
        for disc in discrepancies:
            data.append({
                'id': disc.id,
                'item_type': disc.get_item_type_display(),
                'description': disc.description,
                'previous_amount': disc.previous_amount,
                'new_amount': disc.new_amount,
                'difference': disc.difference,
                'reason': disc.reason,
                'review_status': disc.get_review_status_display(),
                'resolution_status': disc.get_resolution_status_display(),
                'created_at': disc.created_at.strftime('%Y/%m/%d %H:%M'),
                'created_by': disc.created_by.get_full_name() if disc.created_by else 'سیستم'
            })

        return JsonResponse({
            'success': True,
            'discrepancies': data
        })

    except Exception as e:
        logger.error(f"خطا در دریافت مغایرت‌ها: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

# ------------------------------------------------------گزارش صندوق--------------------------
@login_required
def cash_balance_report(request):
    """گزارش موجودی صندوق"""

    # پارامترهای فیلتر
    filter_type = request.GET.get('filter_type', 'monthly')
    branch_id = request.GET.get('branch_id', 'all')

    # مقادیر پیش‌فرض - سال و ماه شمسی
    today_jalali = jdatetime.date.today()

    try:
        year = int(request.GET.get('year', today_jalali.year))
    except:
        year = today_jalali.year

    try:
        month = int(request.GET.get('month', today_jalali.month))
    except:
        month = today_jalali.month

    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    # ایجاد کوئری پایه
    cash_registers = CashRegister.objects.filter(is_verified=True).select_related(
        'branch', 'verified_by', 'created_by'
    ).order_by('-date')

    # فیلتر بر اساس شعبه
    if branch_id != 'all' and branch_id:
        try:
            branch_id_int = int(branch_id)
            cash_registers = cash_registers.filter(branch_id=branch_id_int)
        except (ValueError, TypeError):
            pass

    # فیلتر بر اساس نوع گزارش
    if filter_type == 'monthly':
        try:
            # تبدیل سال و ماه شمسی به میلادی
            jalali_start = jdatetime.date(year, month, 1)

            # محاسبه آخر ماه شمسی
            if month == 12:
                next_month = jdatetime.date(year + 1, 1, 1)
            else:
                next_month = jdatetime.date(year, month + 1, 1)

            jalali_end = next_month - timedelta(days=1)

            gregorian_start = jalali_start.togregorian()
            gregorian_end = jalali_end.togregorian()

            cash_registers = cash_registers.filter(
                date__gte=gregorian_start,
                date__lte=gregorian_end
            )
        except Exception as e:
            print(f"خطا در فیلتر ماهانه: {e}")

    elif filter_type == 'yearly':
        try:
            jalali_start = jdatetime.date(year, 1, 1)
            jalali_end = jdatetime.date(year, 12, 29)

            cash_registers = cash_registers.filter(
                date__gte=jalali_start.togregorian(),
                date__lte=jalali_end.togregorian()
            )
        except Exception as e:
            print(f"خطا در فیلتر سالانه: {e}")

    elif filter_type == 'custom' and start_date and end_date:
        try:
            # تبدیل تاریخ‌های شمسی به میلادی
            start_parts = start_date.split('/')
            end_parts = end_date.split('/')

            if len(start_parts) == 3 and len(end_parts) == 3:
                jalali_start = jdatetime.date(
                    int(start_parts[0]), int(start_parts[1]), int(start_parts[2])
                )
                jalali_end = jdatetime.date(
                    int(end_parts[0]), int(end_parts[1]), int(end_parts[2])
                )

                cash_registers = cash_registers.filter(
                    date__gte=jalali_start.togregorian(),
                    date__lte=jalali_end.togregorian()
                )
        except Exception as e:
            print(f"خطا در فیلتر بازه دلخواه: {e}")

    # محاسبات آماری
    total_cash = cash_registers.aggregate(total=Sum('cash_amount'))['total'] or Decimal('0')
    total_pos = cash_registers.aggregate(total=Sum('pos_amount'))['total'] or Decimal('0')
    total_cheque = cash_registers.aggregate(total=Sum('cheque_amount'))['total'] or Decimal('0')
    total_credit = cash_registers.aggregate(total=Sum('credit_amount'))['total'] or Decimal('0')
    total_investment = cash_registers.aggregate(total=Sum('investment_amount'))['total'] or Decimal('0')

    total_all = total_cash + total_pos + total_cheque + total_credit + total_investment
    record_count = cash_registers.count()

    # محاسبه میانگین نقدی روزانه
    avg_daily_cash = total_cash / Decimal(record_count) if record_count > 0 else Decimal('0')

    # محاسبه بیشترین مبلغ نقدی
    max_cash_record = cash_registers.order_by('-cash_amount').first()
    max_cash = max_cash_record.cash_amount if max_cash_record else Decimal('0')

    # گروه‌بندی بر اساس شعبه
    by_branch = cash_registers.values('branch__id', 'branch__name').annotate(
        cash_total=Sum('cash_amount'),
        pos_total=Sum('pos_amount'),
        cheque_total=Sum('cheque_amount'),
        credit_total=Sum('credit_amount'),
        investment_total=Sum('investment_amount'),
        record_count=Count('id')
    ).order_by('-cash_total')

    # محاسبه مجموع و درصد برای هر شعبه
    for branch in by_branch:
        branch_total = (
                (branch['cash_total'] or Decimal('0')) +
                (branch['pos_total'] or Decimal('0')) +
                (branch['cheque_total'] or Decimal('0')) +
                (branch['credit_total'] or Decimal('0')) +
                (branch['investment_total'] or Decimal('0'))
        )
        branch['total'] = branch_total
        branch['percentage'] = (branch_total / total_all * 100) if total_all > 0 else 0

    # گروه‌بندی بر اساس تاریخ
    by_date = cash_registers.values('date').annotate(
        cash_total=Sum('cash_amount'),
        pos_total=Sum('pos_amount'),
        cheque_total=Sum('cheque_amount'),
        credit_total=Sum('credit_amount'),
        investment_total=Sum('investment_amount'),
        record_count=Count('id')
    ).order_by('-date')[:30]  # 30 روز اخیر

    # لیست سال‌های موجود (شمسی)
    years_jalali = []
    distinct_dates = CashRegister.objects.filter(is_verified=True).dates('date', 'year')
    for date in distinct_dates:
        try:
            jalali_date = jdatetime.date.fromgregorian(date=date)
            if jalali_date.year not in years_jalali:
                years_jalali.append(jalali_date.year)
        except:
            continue

    if not years_jalali:
        years_jalali.append(today_jalali.year)

    years_jalali.sort(reverse=True)

    # اگر سال جاری در لیست نیست، اضافه کن
    if today_jalali.year not in years_jalali:
        years_jalali.insert(0, today_jalali.year)

    # لیست شعب
    branches = Branch.objects.all().order_by('name')

    # پیش‌پردازش رکوردها برای template
    cash_registers_list = []
    for cr in cash_registers:
        try:
            cr.jalali_date = jdatetime.date.fromgregorian(date=cr.date)
            cr.jalali_date_str = cr.jalali_date.strftime('%Y/%m/%d')
            cr.total = cr.total_amount()
        except:
            cr.jalali_date_str = str(cr.date)
            cr.total = Decimal('0')
        cash_registers_list.append(cr)

    # آماده‌سازی context
    context = {
        'cash_registers': cash_registers_list,
        'total_cash': total_cash,
        'total_pos': total_pos,
        'total_cheque': total_cheque,
        'total_credit': total_credit,
        'total_investment': total_investment,
        'total_all': total_all,
        'record_count': record_count,
        'avg_daily_cash': avg_daily_cash,
        'max_cash': max_cash,
        'by_branch': by_branch,
        'by_date': by_date,
        'branches': branches,
        'years': years_jalali,
        'filter_type': filter_type,
        'branch_id': branch_id,
        'selected_year': year,
        'selected_month': month,
        'start_date': start_date,
        'end_date': end_date,
        'today_jalali': today_jalali.strftime('%Y/%m/%d'),
        'persian_months': [
            (1, 'فروردین'), (2, 'اردیبهشت'), (3, 'خرداد'),
            (4, 'تیر'), (5, 'مرداد'), (6, 'شهریور'),
            (7, 'مهر'), (8, 'آبان'), (9, 'آذر'),
            (10, 'دی'), (11, 'بهمن'), (12, 'اسفند')
        ],
    }

    return render(request, 'cash_management/cash_balance_report.html', context)


# در views.py - در بخش توابع کمکی (می‌توانید بعد از get_date_status اضافه کنید)

def get_day_total_from_day_detail(gregorian_date):
    """
    محاسبه مجموع مبلغ روز دقیقاً مثل صفحه جزئیات روز
    از همان منطق day_detail_view استفاده می‌کند
    """
    total = Decimal('0')

    try:
        # همان منطق day_detail_view
        daily_status = DailyCashStatus.objects.filter(date=gregorian_date).first()

        if daily_status:
            # جمع مبالغ شعب
            branch_cashes = DailyBranchCash.objects.filter(daily_status=daily_status)
            for branch_cash in branch_cashes:
                total += branch_cash.cash_amount if branch_cash.cash_amount else Decimal('0')
                total += branch_cash.pos_amount if branch_cash.pos_amount else Decimal('0')

            # جمع سرمایه‌گذاری‌ها
            investments = DailyInvestment.objects.filter(daily_status=daily_status)
            for investment in investments:
                total += investment.investment_amount if investment.investment_amount else Decimal('0')

            # جمع چک‌ها (فقط پاس شده)
            cheques = DailyCheque.objects.filter(daily_status=daily_status, status='passed')
            for cheque in cheques:
                total += cheque.cheque_amount if cheque.cheque_amount else Decimal('0')

            # جمع نسیه‌ها (فقط پرداخت شده)
            credits = DailyCredit.objects.filter(daily_status=daily_status, status='paid')
            for credit in credits:
                total += credit.credit_amount if credit.credit_amount else Decimal('0')
        else:
            # اگر وضعیت روز وجود ندارد، از فاکتورها استفاده کن
            from invoice_app.models import Invoicefrosh

            # جمع فاکتورهای نقدی
            cash_invoices = Invoicefrosh.objects.filter(
                created_at__date=gregorian_date,
                payment_method='cash'
            )
            cash_total = cash_invoices.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')

            # جمع فاکتورهای پوز
            pos_invoices = Invoicefrosh.objects.filter(
                created_at__date=gregorian_date,
                payment_method='pos'
            )
            pos_total = pos_invoices.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')

            total = cash_total + pos_total

    except Exception as e:
        logger.warning(f"خطا در محاسبه مجموع روز {gregorian_date}: {str(e)}")
        total = Decimal('0')

    return total


# سپس در تابع calendar_view، فقط این خط را اضافه کنید:
@login_required
def calendar_view(request):
    """نمایش تقویم - نسخه ساده"""
    today = jdatetime.datetime.now()

    try:
        year = int(request.GET.get('year', today.year))
        month = int(request.GET.get('month', today.month))
    except:
        year, month = today.year, today.month

    month = max(1, min(12, month))

    month_names = [
        'فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
        'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند'
    ]

    # محاسبه تعداد روزهای ماه
    if month <= 6:
        days_in_month = 31
    elif month <= 11:
        days_in_month = 30
    else:
        first_day = jdatetime.datetime(year, 12, 1)
        days_in_month = 30 if first_day.isleap() else 29

    # محاسبه اولین روز هفته
    first_day_obj = jdatetime.datetime(year, month, 1)
    first_weekday = (first_day_obj.weekday() + 2) % 7

    # ایجاد تقویم
    calendar_weeks = []
    day_counter = 0

    for week in range(6):
        week_days = []

        for weekday in range(7):
            if (week == 0 and weekday < first_weekday) or day_counter >= days_in_month:
                day_data = {'day': None, 'status': 'empty', 'total_amount': Decimal('0')}
            else:
                day_number = day_counter + 1
                jdate = jdatetime.datetime(year, month, day_number)
                gregorian_date = jdate.togregorian().date()

                # وضعیت روز
                status = get_date_status(gregorian_date)

                # مجموع مبلغ روز - فقط این خط اضافه شده
                total_amount = get_day_total_from_day_detail(gregorian_date)

                is_today = (year == today.year and month == today.month and day_number == today.day)

                day_data = {
                    'day': day_number,
                    'year': year,
                    'month': month,
                    'jalali_date': f"{year}/{month}/{day_number}",
                    'gregorian_date': gregorian_date,
                    'is_current_month': True,
                    'is_today': is_today,
                    'status': status,
                    'total_amount': total_amount  # اضافه شده
                }
                day_counter += 1

            week_days.append(day_data)

        calendar_weeks.append(week_days)

    context = {
        'calendar_data': calendar_weeks,
        'current_year': year,
        'current_month': month,
        'current_month_name': month_names[month - 1],
        'year_range': range(year - 5, year + 6),
    }

    return render(request, 'cash_management/calendar.html', context)