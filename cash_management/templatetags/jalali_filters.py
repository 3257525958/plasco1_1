from django import template
import jdatetime
from django.contrib.humanize.templatetags.humanize import intcomma as django_intcomma
import locale

register = template.Library()


@register.filter
def to_jalali(value, date_format='%Y/%m/%d'):
    """تبدیل تاریخ میلادی به شمسی"""
    if not value:
        return ''

    try:
        if hasattr(value, 'jalali_date_str'):
            return value.jalali_date_str

        # اگر رشته است، ابتدا به تاریخ تبدیل کنیم
        if isinstance(value, str):
            from datetime import datetime
            value = datetime.strptime(value, '%Y-%m-%d').date()

        # تبدیل به تاریخ شمسی
        jalali_date = jdatetime.date.fromgregorian(date=value)
        return jalali_date.strftime(date_format)
    except Exception:
        # در صورت خطا، تاریخ میلادی را نمایش بده
        try:
            return str(value.strftime('%Y-%m-%d'))
        except:
            return str(value)


@register.filter
def persian_intcomma(value, use_floatformat=True):
    """قالب‌بندی اعداد با جداکننده فارسی"""
    if value is None:
        return '۰'

    try:
        # اگر رشته است، به عدد تبدیل کن
        if isinstance(value, str):
            value = value.replace(',', '')

        # تبدیل به عدد
        num = float(value) if '.' in str(value) else int(value)

        # فرمت کردن با جداکننده هزارگان
        if use_floatformat and isinstance(value, float):
            # برای اعداد اعشاری
            formatted = f"{num:,.2f}"
        else:
            # برای اعداد صحیح
            formatted = f"{int(num):,}"

        # تبدیل اعداد انگلیسی به فارسی و کاما به جداکننده فارسی
        persian_numbers = '۰۱۲۳۴۵۶۷۸۹'
        english_numbers = '0123456789'

        # تبدیل ارقام
        for en, fa in zip(english_numbers, persian_numbers):
            formatted = formatted.replace(en, fa)

        # تبدیل جداکننده
        formatted = formatted.replace(",", "٬")

        return formatted
    except Exception as e:
        print(f"خطا در persian_intcomma: {e}")
        return str(value)


@register.filter
def divide(value, arg):
    """تقسیم دو عدد"""
    try:
        result = float(value) / float(arg)
        return round(result, 2)
    except (ValueError, ZeroDivisionError):
        return 0


@register.filter
def multiply(value, arg):
    """ضرب دو عدد"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def payment_method_display(value):
    """نمایش فارسی روش پرداخت"""
    methods = {
        'cash': 'نقدی',
        'bank_transfer': 'واریز به حساب'
    }
    return methods.get(value, value)


@register.filter
def month_name_fa(month_number):
    """نام فارسی ماه"""
    months = {
        1: 'فروردین', 2: 'اردیبهشت', 3: 'خرداد',
        4: 'تیر', 5: 'مرداد', 6: 'شهریور',
        7: 'مهر', 8: 'آبان', 9: 'آذر',
        10: 'دی', 11: 'بهمن', 12: 'اسفند'
    }
    return months.get(int(month_number), '')


@register.filter
def to_persian_digits(value):
    """تبدیل اعداد انگلیسی به فارسی"""
    if value is None:
        return ''

    persian_numbers = '۰۱۲۳۴۵۶۷۸۹'
    english_numbers = '0123456789'

    result = str(value)
    for en, fa in zip(english_numbers, persian_numbers):
        result = result.replace(en, fa)

    return result


# فیلتر برای format با آرگومان‌های پویا
@register.filter
def format_string(value, arg):
    """قالب‌بندی رشته با استفاده از جایگذاری"""
    try:
        return arg.format(value)
    except:
        return value