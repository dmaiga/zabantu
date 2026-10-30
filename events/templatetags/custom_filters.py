# events/templatetags/custom_filters.py
from django import template

register = template.Library()

@register.filter
def split(value, delimiter=','):
    """Filtre pour diviser une chaîne en liste"""
    return value.split(delimiter)