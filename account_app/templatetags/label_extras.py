from django import template

register = template.Library()

@register.filter
def get_range(value):
    """تولید range برای template"""
    return range(1, int(value) + 1)