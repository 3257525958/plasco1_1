# account_app/templatetags/label_extras.py
from django import template
import math

register = template.Library()

@register.filter
def get_range(value):
    """تولید range برای template"""
    try:
        return range(1, int(value) + 1)
    except (ValueError, TypeError):
        return range(1)

@register.filter
def multiply(value, arg):
    """ضرب دو عدد در template"""
    try:
        return int(value) * int(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def divide(value, arg):
    """تقسیم دو عدد در template"""
    try:
        return int(value) / int(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

@register.filter
def ceil(value):
    """گرد کردن به بالا"""
    try:
        return math.ceil(float(value))
    except (ValueError, TypeError):
        return 0

@register.filter
def chunk(value, arg):
    """تقسیم لیست به بخش‌های n تایی"""
    try:
        chunk_size = int(arg)
        return [value[i:i + chunk_size] for i in range(0, len(value), chunk_size)]
    except (ValueError, TypeError):
        return [value]