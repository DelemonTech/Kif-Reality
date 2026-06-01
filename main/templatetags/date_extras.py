# yourapp/templatetags/date_extras.py
from django import template
import calendar

register = template.Library()

@register.filter
def format_delivery(value):
    """
    Expects integer like 202503 -> March 2025
    """
    try:
        value = int(value)
        year = value // 100
        month = value % 100

        if 1 <= month <= 12:
            month_name = calendar.month_abbr[month]  # "Jan", "Feb" ...
            return f"{month_name} {year}"
        else:
            return "Invalid Date"
    except Exception:
        return "N/A"
