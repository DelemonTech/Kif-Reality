# main/templatetags/custom_filters.py
from django import template

register = template.Library()

@register.simple_tag
def url_replace(request, field, value):
    """Replace a URL parameter while maintaining others"""
    dict_ = request.GET.copy()
    dict_[field] = value
    return dict_.urlencode()

@register.filter
def add_commas(value):
    """
    Format integer/float with thousand separators. If float, drop decimal if .0
    """
    if value is None:
        return ''
    try:
        # If float has .0, convert to int for nicer formatting
        if isinstance(value, float) and value.is_integer():
            iv = int(value)
            return f"{iv:,}"
        return f"{int(value):,}"
    except (ValueError, TypeError):
        # fallback to string if not numeric
        try:
            s = str(value)
            parts = s.split('.')
            parts[0] = "{:,}".format(int(parts[0]))
            return '.'.join(parts)
        except Exception:
            return s

@register.filter
def multiply(value, arg):
    """Multiply two values"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0
    
@register.filter
def percentage(value, total):
    """Calculate percentage"""
    try:
        return round((float(value) / float(total)) * 100, 1)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0
