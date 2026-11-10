"""Balises d'aperçu des liens partagés (Open Graph), sitemap et balise canonique.

Les balises sont générées à l'affichage : aucune URL ni donnée en base ne change. La balise canonique et le sitemap ne
concernent que les contenus publiés à partir de SEO_START_DATE ; les plus anciens restent tels quels.
"""
import datetime
import re

from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from zabantu.i18n import current_language, is_blank, translated

from .sanitize import plain_text
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
    text = re.sub(r'\s+', ' ', plain_text(value)).strip()
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
    'home': (_('Zabantu - Groupe de recherche : Economy | Conflict | State'),
             _("Groupe de chercheurs en sciences sociales travaillant sur le développement économique et social.")),
    'public_article_list': (_('Publications - Zabantu'), _("Analyses, articles, ouvrages, policy briefs et rapports du groupe de recherche Zabantu.")),
    'public_event_list': (_('Événements - Zabantu'), _("Séminaires Gɛlɛkan, conférences, ateliers et webinaires du groupe de recherche Zabantu.")),
    'public_member_list': (_('Membres - Zabantu'), _("Les chercheurs et chercheuses du groupe de recherche Zabantu.")),
    'about': (_('Qui sommes-nous - Zabantu'), _("Zabantu est un groupe de recherche pluridisciplinaire sur le nexus Economy | Conflict | State.")),
    'liste_galeries': (_('Galerie photos - Zabantu'), _("Les photos des séminaires et activités du groupe de recherche Zabantu.")),
    'toutes_photos': (_('Galerie photos - Zabantu'), _("Toutes les photos du groupe de recherche Zabantu.")),
    'contact': (_('Contact - Zabantu'), _("Écrivez au groupe de recherche Zabantu : collaboration, information, questions.")),
    'donate': (_('Faire un don - Zabantu'), _("Soutenez le groupe de recherche Zabantu : vos dons financent la recherche, les séminaires Gɛlɛkan et les publications.")),
    'membership_apply': (_('Rejoindre Zabantu'), _("Faites une demande d'adhésion au groupe de recherche Zabantu.")),
}


def page_seo(request):
    """Titre, description et canonical d'une page publique sans contenu propre."""
    match = getattr(request, 'resolver_match', None)
    found = PAGE_SEO.get(match.url_name) if match else None
    return {
        'title': str(found[0]),
        'description': str(found[1]),
        'canonical': origin() + request.path,
    } if found else {}


def _description(obj, *fields):
    """Premier texte rempli pour la description de partage. En anglais, la version anglaise passe avant la
    description SEO (rédigée en français) ; le français reste le dernier recours."""
    if current_language() != settings.LANGUAGE_CODE:
        for name in fields:
            value = getattr(obj, f'{name}_{current_language()}', None)
            if not is_blank(value):
                return value
    for name in ('meta_description',) + fields:
        value = getattr(obj, name, None)
        if not is_blank(value):
            return value
    return ''


def gallery_seo(request, gallery):
    return build(request, gallery, title=translated(gallery, 'title'),
                 description=_description(gallery, 'description') or PAGE_SEO['liste_galeries'][1],
                 image=gallery.cover_image)


def member_seo(request, member):
    return build(request, member, title=f'{member.get_full_name()} - Zabantu',
                 description=translated(member, 'bio') or translated(member, 'job_title') or PAGE_SEO['public_member_list'][1],
                 image=member.profile_picture)


def article_seo(request, article):
    return build(
        request, article,
        title=translated(article, 'title'),
        description=_description(article, 'subtitle', 'content'),
        image=article.cover_image or article.independent_cover,
        type_='article', published=article.publish_at,
    )


def guelekan_seo(request, guelekan):
    return build(
        request, guelekan,
        title=translated(guelekan, 'title'),
        description=_description(guelekan, 'subtitle', 'content'),
        image=guelekan.cover_image,
        type_='article', published=guelekan.publish_at,
    )


def event_seo(request, event):
    return build(request, event, title=translated(event, 'title'), description=_description(event, 'content'),
                 image=event.image)
