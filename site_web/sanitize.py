"""Nettoyage du HTML saisi dans les éditeurs de texte avant affichage.

Appliqué à l'affichage : les contenus enregistrés ne sont jamais modifiés. Liste blanche de balises, d'attributs et de
propriétés CSS établie d'après les contenus réels (paragraphes, titres, listes, liens, couleurs et polices du copier-coller).
"""
import html
import re

import bleach
from django.utils.html import strip_tags
from django.utils.safestring import mark_safe

TAGS = {
    'p', 'br', 'hr', 'div', 'span', 'font', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'strong', 'b', 'em', 'i', 'u', 's', 'strike', 'sub', 'sup', 'small', 'mark',
    'ul', 'ol', 'li', 'blockquote', 'pre', 'code', 'a', 'img', 'figure', 'figcaption',
    'table', 'thead', 'tbody', 'tfoot', 'tr', 'th', 'td', 'caption',
}
ATTRIBUTES = {
    '*': {'style', 'class'},
    'a': {'href', 'title', 'target', 'rel'},
    'img': {'src', 'alt', 'title', 'width', 'height'},
    'font': {'color', 'size', 'face'},
    'td': {'colspan', 'rowspan'}, 'th': {'colspan', 'rowspan'},
}
PROTOCOLS = {'http', 'https', 'mailto', 'tel'}
CSS_PROPERTIES = {
    'color', 'background-color', 'font-family', 'font-size', 'font-weight', 'font-style', 'text-align',
    'text-decoration', 'line-height', 'margin', 'margin-top', 'margin-bottom', 'margin-left', 'margin-right',
    'padding', 'padding-top', 'padding-bottom', 'padding-left', 'padding-right',
    'border', 'border-top', 'border-bottom', 'border-left', 'border-right', 'border-width', 'border-style',
    'border-color', 'width', 'height', 'list-style-type',
}
# Le contenu des balises script et style est supprimé avec elles (bleach ne garderait que leur texte)
DROP_BLOCKS = re.compile(r'<(script|style)\b.*?</\1\s*>', re.IGNORECASE | re.DOTALL)
UNSAFE_CSS_VALUE = re.compile(r'url\s*\(|expression|javascript:|@import|[<>\\]', re.IGNORECASE)


class StyleSanitizer:
    """Garde les déclarations CSS connues et sans valeur dangereuse, retire les autres (le style reste utilisable).

    bleach accepte tout objet doté d'une méthode sanitize_css ; cela évite d'ajouter la dépendance tinycss2."""

    def sanitize_css(self, style):
        kept = []
        # bleach transmet la valeur encore échappée (&quot; contient un « ; » qui couperait la déclaration)
        for declaration in filter(None, (d.strip() for d in html.unescape(style).split(';'))):
            prop, sep, value = declaration.partition(':')
            if sep and prop.strip().lower() in CSS_PROPERTIES and not UNSAFE_CSS_VALUE.search(value):
                kept.append(f'{prop.strip().lower()}: {value.strip()}')
        return '; '.join(kept) + (';' if kept else '')


def _allow_attribute(tag, name, value):
    return name in (ATTRIBUTES.get(tag, set()) | ATTRIBUTES['*'])


_cleaner = bleach.Cleaner(tags=TAGS, attributes=_allow_attribute, protocols=PROTOCOLS, strip=True,
                          css_sanitizer=StyleSanitizer())


def clean_html(value):
    """HTML nettoyé et marqué sûr ; chaîne vide pour une valeur vide."""
    if not value:
        return ''
    return mark_safe(_cleaner.clean(DROP_BLOCKS.sub('', str(value))))


def plain_text(value):
    """Texte brut d'un contenu HTML (balises retirées, entités décodées) : à afficher échappé, jamais en « safe »."""
    return html.unescape(strip_tags(DROP_BLOCKS.sub('', str(value or ''))))
