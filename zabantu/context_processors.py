from django.conf import settings
from django.templatetags.static import static

def global_settings(request):
    from site_web.seo import page_seo
    user = getattr(request, 'user', None)
    pending = 0
    unread = 0
    if user is not None and user.is_authenticated and getattr(user, 'role', '') in ('admin', 'moderateur'):
        from site_web.models import MembershipApplication
        pending = MembershipApplication.objects.filter(
            status=MembershipApplication.Status.PENDING).count()
        from site_web.models import ContactMessage
        unread = ContactMessage.objects.filter(is_read=False).count()
    from django.utils.functional import SimpleLazyObject
    from site_web.content_cache import content_version
    return {
        **language_links(request),
        'content_version': SimpleLazyObject(content_version),  # lu seulement par les gabarits qui en ont besoin
        'PAGE_CACHE_TIMEOUT': settings.PAGE_CACHE_TIMEOUT,
        'pending_applications_count': pending,
        'unread_messages_count': unread,
        'DEFAULT_FROM_EMAIL': settings.DEFAULT_FROM_EMAIL,
        'DEFAULT_FROM_EMAIL_NEWS': settings.DEFAULT_FROM_EMAIL_NEWS,
        'seo': page_seo(request),
        'SITE_URL': settings.SITE_URL,
        'SITE_ORIGIN': settings.SITE_URL.rstrip('/'),
        'SEO_DEFAULT_IMAGE': settings.SITE_URL.rstrip('/') + static('site_web/images/og-default.jpg'),
    }


ALTERNATE_PARAMS = ('type', 'page', 'gallery', 'tag')


def language_links(request):
    """Adresse de la page courante dans chaque langue : sélecteur de langue (filtres et page conservés) et balises
    hreflang (chemin seul). Vide pour les pages qui n'existent que dans une langue (backoffice, page introuvable)."""
    from django.urls import translate_url
    from zabantu.i18n import current_language
    codes = [code for code, _name in settings.LANGUAGES]
    # hreflang : filtres et page gardés (pages distinctes), recherche et tri retirés (variantes sans valeur propre)
    kept = request.GET.copy()
    for name in list(kept):
        if name not in ALTERNATE_PARAMS:
            del kept[name]
    path = request.path + (f'?{kept.urlencode()}' if kept else '')
    paths = {code: translate_url(path, code) for code in codes}
    if len(set(paths.values())) < 2:
        return {'alternate_urls': {}, 'alternate_paths': {}, 'other_language': None, 'og_locale': 'fr_FR'}
    language = current_language()
    other = next(code for code in codes if code != language)
    return {
        'alternate_paths': paths,
        'alternate_urls': {code: translate_url(request.get_full_path(), code) for code in codes},
        'other_language': other,
        'other_language_url': translate_url(request.get_full_path(), other),
        'og_locale': 'en_GB' if language == 'en' else 'fr_FR',
    }
