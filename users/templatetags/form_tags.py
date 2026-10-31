from django import forms, template

register = template.Library()

BOOTSTRAP_CLASSES = {'form-control', 'form-select', 'form-check-input', 'is-invalid'}
SELF_STYLED = (forms.RadioSelect, forms.CheckboxSelectMultiple)


def _is_rich_text(widget):
    # Les éditeurs de texte riche (Summernote, TinyMCE) gèrent leur propre rendu
    return widget.__class__.__name__ in ('SummernoteWidget', 'SummernoteInplaceWidget', 'TinyMCE')


@register.filter
def is_checkbox(field):
    return isinstance(field.field.widget, forms.CheckboxInput)


@register.filter
def bootstrap(field):
    """Affiche le champ avec les classes Bootstrap adaptées à son type, sans toucher au widget du formulaire."""
    widget = field.field.widget
    if _is_rich_text(widget) or isinstance(widget, SELF_STYLED):
        return field.as_widget()
    if isinstance(widget, forms.CheckboxInput):
        css = 'form-check-input'
    elif isinstance(widget, forms.Select):  # inclut SelectMultiple
        css = 'form-select'
    else:
        css = 'form-control'
    kept = [c for c in widget.attrs.get('class', '').split() if c not in BOOTSTRAP_CLASSES]
    classes = kept + [css] + (['is-invalid'] if field.errors else [])
    return field.as_widget(attrs={'class': ' '.join(classes)})


@register.filter
def has_errors(fields):
    """Vrai si l'un des champs de la section a une erreur."""
    return any(field.errors for field in fields)
