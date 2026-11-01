from django import template

from site_web import sanitize

register = template.Library()


@register.filter
def clean_html(value):
    """{{ article.content|clean_html }} : remplace |safe pour le contenu saisi dans un éditeur de texte riche."""
    return sanitize.clean_html(value)


@register.filter
def plain_text(value):
    """{{ article.title|plain_text }} : texte sans balises, échappé à l'affichage."""
    return sanitize.plain_text(value)
