"""Balises d'aperçu des liens partagés (Open Graph), sitemap et balise canonique.

Les balises sont générées à l'affichage : aucune URL ni donnée en base ne change. La balise canonique et le sitemap ne
concernent que les contenus publiés à partir de SEO_START_DATE ; les plus anciens restent tels quels.
"""
import datetime
import html
import re

from django.conf import settings
from django.utils import timezone
from django.utils.html import strip_tags

from .thumbnails import get_thumbnail

SHARE_IMAGE_WIDTH = 1200
DESCRIPTION_MAX = 160


def origin():
    return settings.SITE_URL.rstrip('/')


def absolute_url(url):
    """Adresse complète : SITE_URL + chemin, sauf si l'adresse l'est déjà."""
    if not url:
        return ''
    return url if re.match(r'^https?://', url) else origin() + url


def clean_text(value, limit=DESCRIPTION_MAX):
    """Texte brut d'un contenu HTML, espaces regroupés, raccourci à `limit` caractères."""
    text = re.sub(r'\s+', ' ', html.unescape(strip_tags(str(value or '')))).strip()
    return text if len(text) <= limit else text[:limit - 1].rstrip() + '…'


def start_datetime():
    return timezone.make_aware(datetime.datetime.combine(settings.SEO_START_DATE, datetime.time.min))


def is_new(obj):
    """Vrai pour un contenu publié (ou créé, à défaut) à partir de la date de départ."""
    moment = getattr(obj, 'publish_at', None) or obj.created_at
    return moment >= start_datetime()


def share_image(image):
    """Adresse complète d'une version 1200 px de l'image ; vide si le contenu n'en a pas (image par défaut du site)."""
    if not image:
        return ''
    return absolute_url(get_thumbnail(image, SHARE_IMAGE_WIDTH).url)


def build(request, obj, *, title, description, image=None, type_='website', published=None):
    seo = {
        'title': title,
        'description': clean_text(description),
        'image': share_image(image),
        'type': type_,
    }
    if published:
        seo['published'] = published.isoformat()
    if is_new(obj):
        seo['canonical'] = origin() + request.path
    return seo


# Titres de partage des pages sans contenu propre (listes, présentation). Les vues de détail les remplacent.
PAGE_SEO = {
    'public_article_list': ('Publications - Zabantu', "Analyses, articles, ouvrages, policy briefs et rapports du groupe de recherche Zabantu."),
    'public_event_list': ('Événements - Zabantu', "Séminaires Gɛlɛkan, conférences, ateliers et webinaires du groupe de recherche Zabantu."),
    'public_member_list': ('Membres - Zabantu', "Les chercheurs et chercheuses du groupe de recherche Zabantu."),
    'about': ('Qui sommes-nous - Zabantu', "Zabantu est un groupe de recherche pluridisciplinaire sur le nexus Economy | Conflict | State."),
    'liste_galeries': ('Galerie photos - Zabantu', "Les photos des séminaires et activités du groupe de recherche Zabantu."),
    'toutes_photos': ('Galerie photos - Zabantu', "Toutes les photos du groupe de recherche Zabantu."),
    'contact': ('Contact - Zabantu', "Écrivez au groupe de recherche Zabantu : collaboration, information, questions."),
    'membership_apply': ('Rejoindre Zabantu', "Faites une demande d'adhésion au groupe de recherche Zabantu."),
}


def page_seo(request):
    """Titre et description de partage d'une page sans contenu propre ; vide pour l'accueil et les autres pages."""
    match = getattr(request, 'resolver_match', None)
    found = PAGE_SEO.get(match.url_name) if match else None
    return {'title': found[0], 'description': found[1]} if found else {}


def gallery_seo(request, gallery):
    return build(request, gallery, title=gallery.title, description=gallery.description or PAGE_SEO['liste_galeries'][1],
                 image=gallery.cover_image)


def article_seo(request, article):
    return build(
        request, article,
        title=article.title,
        description=article.meta_description or article.subtitle or article.content,
        image=article.cover_image or article.independent_cover,
        type_='article', published=article.publish_at,
    )


def guelekan_seo(request, guelekan):
    return build(
        request, guelekan,
        title=guelekan.title,
        description=guelekan.meta_description or guelekan.subtitle or guelekan.content,
        image=guelekan.cover_image,
        type_='article', published=guelekan.publish_at,
    )


def event_seo(request, event):
    return build(request, event, title=event.title, description=event.content, image=event.image)
