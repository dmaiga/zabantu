"""Fichiers à la racine du site : /sitemap.xml et /robots.txt."""
from django.conf import settings
from django.db.models import Count, Q
from django.http import HttpResponse
from django.urls import reverse
from django.utils import timezone, translation
from django.utils.xmlutils import SimplerXMLGenerator
from django.views.decorators.http import require_GET

from articles.models import Article, Guelekan
from events.models import Event
from gallery.models import Gallery
from users.models import CustomUser

from . import seo

# Zones privées (connexion obligatoire). Aucune page publique ni /media/ n'y figure.
PRIVATE_PATHS = ('/admin/', '/auth/', '/users/', '/articles/', '/events/', '/gallery/', '/intervenants/',
                 '/courses/', '/tinymce/', '/password-reset', '/zabantu/compte/', '/en/zabantu/compte/')


STATIC_ENTRIES = ('home', 'public_article_list', 'public_event_list', 'public_member_list', 'liste_galeries', 'about')


def _entries():
    """(contenu éventuel, nom d'URL, arguments, dernière modification) des pages publiques retenues."""
    start, now = seo.start_datetime(), timezone.now()
    for name in STATIC_ENTRIES:
        yield None, name, [], None
    for article in Article.objects.filter(status='published', publish_at__gte=start, publish_at__lte=now):
        yield article, 'public_article_detail', [article.slug], article.updated_at
    guelekan_date = Q(publish_at__gte=start, publish_at__lte=now) | Q(publish_at__isnull=True, created_at__gte=start)
    for g in Guelekan.objects.filter(guelekan_date, status='published'):
        yield g, 'public_guelekan_detail', [g.slug], g.updated_at
    for event in Event.objects.filter(status='published', created_at__gte=start):
        yield event, 'public_event_detail', [event.pk], event.updated_at
    for member in CustomUser.objects.filter(is_active=True, role__in=('moderateur', 'membre')):
        yield member, 'public_member_detail', [member.pk], member.updated_at
    for gallery in Gallery.objects.annotate(photo_total=Count('photos')).filter(photo_total__gt=0):
        yield gallery, 'detail_galerie', [gallery.slug], gallery.updated_at


def _addresses(obj, name, args):
    """{langue: adresse complète} de la page dans chaque langue où elle est traduite (le français toujours) :
    une page anglaise dont le contenu principal reste en français n'est pas annoncée (voir page_translation_context)."""
    addresses = {}
    for code, _name in settings.LANGUAGES:
        if obj is None or code == settings.LANGUAGE_CODE or obj.is_translated(code):
            with translation.override(code):
                addresses[code] = seo.origin() + reverse(name, args=args)
    return addresses


@require_GET
def sitemap(request):
    response = HttpResponse(content_type='application/xml; charset=utf-8')
    xml = SimplerXMLGenerator(response, 'utf-8')
    xml.startDocument()
    xml.startElement('urlset', {'xmlns': 'http://www.sitemaps.org/schemas/sitemap/0.9',
                                'xmlns:xhtml': 'http://www.w3.org/1999/xhtml'})
    # Une entrée par langue, chacune annonçant toutes les versions (hreflang), comme les balises des pages
    for obj, name, args, modified in _entries():
        addresses = _addresses(obj, name, args)
        for address in addresses.values():
            xml.startElement('url', {})
            xml.addQuickElement('loc', address)
            if modified:
                xml.addQuickElement('lastmod', modified.date().isoformat())
            if len(addresses) > 1:
                for code, alternate in addresses.items():
                    xml.addQuickElement('xhtml:link', attrs={'rel': 'alternate', 'hreflang': code, 'href': alternate})
                xml.addQuickElement('xhtml:link', attrs={'rel': 'alternate', 'hreflang': 'x-default',
                                                         'href': addresses[settings.LANGUAGE_CODE]})
            xml.endElement('url')
    xml.endElement('urlset')
    xml.endDocument()
    return response


@require_GET
def robots(request):
    lines = ['User-agent: *'] + [f'Disallow: {p}' for p in PRIVATE_PATHS] + [
        '', f'Sitemap: {seo.origin()}/sitemap.xml', '']
    return HttpResponse('\n'.join(lines), content_type='text/plain; charset=utf-8')
