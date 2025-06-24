# Create this file: your_app/templatetags/custom_filters.py

from django import template
from datetime import datetime, date

register = template.Library()


@register.filter
def days_from_today(expiry_date):
    """Calculate days difference from today"""
    if isinstance(expiry_date, str):
        expiry_date = datetime.strptime(expiry_date, '%Y-%m-%d').date()

    today = date.today()
    return (expiry_date - today).days


@register.filter
def abs_value(value):
    """Return absolute value"""
    return abs(value)