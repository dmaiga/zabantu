from django import template
from django.utils import timezone

register = template.Library()


def _compact(seconds):
    minutes = int(seconds // 60)
    if minutes < 1:
        return "moins d'une minute"
    if minutes < 60:
        return f'{minutes} min'
    hours = minutes // 60
    if hours < 24:
        return f'{hours} h'
    days = hours // 24
    if days < 14:
        return f'{days} j'
    if days < 60:
        return f'{days // 7} sem.'
    return f'{days // 30} mois'


@register.filter
def since_short(value):
    """« 15 min », « 2 h », « 3 j » : durée écoulée, en une seule unité."""
    return _compact((timezone.now() - value).total_seconds())


@register.filter
def until_short(value):
    """Durée restante avant `value`, en une seule unité."""
    return _compact((value - timezone.now()).total_seconds())
