from django import template

from site_web.thumbnails import get_thumbnail

register = template.Library()


@register.simple_tag
def thumb(image, width=640):
    """{% thumb photo.image 640 as t %} puis t.url, t.width, t.height, t.src_width, t.src_height"""
    return get_thumbnail(image, int(width))
