from django import template

from site_web.thumbnails import get_thumbnail

register = template.Library()


@register.simple_tag
def thumb(image, width=640):
    """{% thumb photo.image 640 as t %} puis t.url, t.width, t.height, t.src_width, t.src_height"""
    return get_thumbnail(image, int(width))


@register.filter
def thumb_url(image, width=640):
    """{{ article.cover_image|thumb_url:640 }} : adresse de la miniature (ou de l'original en repli)."""
    return get_thumbnail(image, int(width)).url if image else ''
