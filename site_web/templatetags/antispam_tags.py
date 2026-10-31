from django import template
from django.utils.html import format_html

from .. import antispam

register = template.Library()


@register.simple_tag
def antispam_fields():
    """Champ piège (invisible, hors écran) et heure signée d'affichage du formulaire."""
    return format_html(
        '<div aria-hidden="true" style="position:absolute;left:-10000px;top:auto;width:1px;height:1px;overflow:hidden;">'
        '<label for="id_{hp}">Ne pas remplir ce champ</label>'
        '<input type="text" name="{hp}" id="id_{hp}" value="" tabindex="-1" autocomplete="off"></div>'
        '<input type="hidden" name="{ts}" value="{stamp}">',
        hp=antispam.HONEYPOT, ts=antispam.STAMP, stamp=antispam.new_stamp())
