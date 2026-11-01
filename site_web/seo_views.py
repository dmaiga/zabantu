"""Fichiers à la racine du site : /sitemap.xml et /robots.txt."""
from django.http import HttpResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.xmlutils import SimplerXMLGenerator
from django.views.decorators.http import require_GET

from articles.models import Article, Guelekan
from events.models import Event

from . import seo

# Zones privées (connexion obligatoire). Aucune page publique ni /media/ n'y figure.
PRIVATE_PATHS = ('/admin/', '/auth/', '/users/', '/articles/', '/events/', '/gallery/', '/intervenants/',
                 '/tinymce/', '/password-reset')


def _entries():
    """(adresse, dernière modification) des contenus publiés à partir de SEO_START_DATE."""
    start, now = seo.start_datetime(), timezone.now()
    for article in Article.objects.filter(status='published', publish_at__gte=start, publish_at__lte=now):
        yield reverse('public_article_detail', args=[article.slug]), article.updated_at
    for g in Guelekan.objects.filter(status='published', publish_at__gte=start, publish_at__lte=now):
        yield reverse('public_guelekan_detail', args=[g.slug]), g.updated_at
    for event in Event.objects.filter(status='published', created_at__gte=start):
        yield reverse('public_event_detail', args=[event.pk]), event.updated_at


@require_GET
def sitemap(request):
    response = HttpResponse(content_type='application/xml; charset=utf-8')
    xml = SimplerXMLGenerator(response, 'utf-8')
    xml.startDocument()
    xml.startElement('urlset', {'xmlns': 'http://www.sitemaps.org/schemas/sitemap/0.9'})
    for path, modified in _entries():
        xml.startElement('url', {})
        xml.addQuickElement('loc', seo.origin() + path)
        xml.addQuickElement('lastmod', modified.date().isoformat())
        xml.endElement('url')
    xml.endElement('urlset')
    xml.endDocument()
    return response


@require_GET
def robots(request):
    lines = ['User-agent: *'] + [f'Disallow: {p}' for p in PRIVATE_PATHS] + [
        '', f'Sitemap: {seo.origin()}/sitemap.xml', '']
    return HttpResponse('\n'.join(lines), content_type='text/plain; charset=utf-8')
