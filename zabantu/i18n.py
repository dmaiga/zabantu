"""Site bilingue français / anglais.

- La langue vient de l'adresse seule : /en/… en anglais, tout le reste en français. Le backoffice (/users/, /articles/…)
  n'est jamais préfixé : il reste en français quel que soit le navigateur (PathLanguageMiddleware).
- Contenus : les champs existants sont le français. Les champs « _en » sont facultatifs ; vides, le français s'affiche.
  Dans les gabarits : {{ article.t.title }} au lieu de {{ article.title }} (modèles dotés de TranslatableMixin).
"""
import re

from django.conf import settings
from django.utils import translation

ENGLISH = 'en'


def current_language():
    return (translation.get_language() or settings.LANGUAGE_CODE)[:2]


def is_blank(value):
    """Vrai pour une valeur vide, y compris un texte riche sans contenu (« <p><br></p> », espaces insécables)."""
    if value is None:
        return True
    if not isinstance(value, str):
        return False
    if re.search(r'<(img|iframe|video|audio|object|embed)\b', value, re.I):
        return False
    text = re.sub(r'<[^>]*>', '', value).replace('&nbsp;', ' ').replace('\xa0', ' ')
    return not text.strip()


def translated(obj, name, language=None):
    """Valeur du champ `name` dans la langue demandée (langue active par défaut), le français à défaut."""
    language = (language or current_language())[:2]
    if language != settings.LANGUAGE_CODE:
        value = getattr(obj, f'{name}_{language}', None)
        if not is_blank(value):
            return value
    return getattr(obj, name)


def shown_language(obj, name, language=None):
    """Langue réellement affichée pour le champ `name` : la langue demandée si sa version est remplie, le français
    sinon. Sert à l'attribut lang des contenus restés en français sur une page anglaise."""
    language = (language or current_language())[:2]
    if language != settings.LANGUAGE_CODE and not is_blank(getattr(obj, f'{name}_{language}', None)):
        return language
    return settings.LANGUAGE_CODE


class TranslatedFields:
    """Vue d'un objet dans la langue active : `obj.t.title` vaut `title_en` en anglais s'il est rempli.
    `obj.t.lang_title` donne la langue affichée (« fr » si le français sert de repli), pour l'attribut HTML lang."""

    def __init__(self, obj):
        self._obj = obj

    def __getattr__(self, name):
        if name.startswith('lang_'):
            return shown_language(self._obj, name[5:])
        return translated(self._obj, name)


class TranslatableMixin:
    """À ajouter aux modèles qui ont des champs « _en ».

    TRANSLATED_FIELDS : champs traduisibles (recherche, formulaires du backoffice).
    MAIN_FIELDS : contenu principal de la page publique. Un nom seul doit être traduit s'il est rempli en français ;
    un tuple demande qu'au moins un de ses champs remplis en français le soit aussi en anglais (corps du texte,
    résumé…). Tant que ce n'est pas le cas, la page anglaise n'est pas proposée aux moteurs de recherche."""
    TRANSLATED_FIELDS = ()
    MAIN_FIELDS = ()

    @property
    def t(self):
        return TranslatedFields(self)

    def is_translated(self, language=ENGLISH):
        def filled(name, lang=None):
            return not is_blank(getattr(self, f'{name}_{lang}' if lang else name, None))
        for rule in self.MAIN_FIELDS:
            group = rule if isinstance(rule, tuple) else (rule,)
            in_french = [name for name in group if filled(name)]
            if in_french and not any(filled(name, language) for name in in_french):
                return False
        return bool(self.MAIN_FIELDS)


def page_translation_context(obj):
    """Contexte d'une page de détail dont le contenu n'est pas encore traduit : la version anglaise reste consultable
    (repli sur le français) mais n'est ni annoncée (hreflang, sitemap) ni indexée (noindex). Vide si traduite."""
    if obj.is_translated():
        return {}
    return {'alternate_paths': {}, 'robots_noindex': current_language() != settings.LANGUAGE_CODE}


class PathLanguageMiddleware:
    """Active la langue indiquée par le préfixe de l'adresse (/en/…), le français sinon.

    Remplace LocaleMiddleware, qui suivrait aussi la langue du navigateur et le cookie : un visiteur anglophone verrait
    alors le backoffice et les adresses sans préfixe en anglais."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        language = translation.get_language_from_path(request.path_info) or settings.LANGUAGE_CODE
        translation.activate(language)
        request.LANGUAGE_CODE = language
        try:
            response = self.get_response(request)
        finally:
            # La langue reste propre à la requête : le fil d'exécution suivant (autre requête, tests) repart du français
            translation.deactivate()
        response.headers.setdefault('Content-Language', language)
        return response
