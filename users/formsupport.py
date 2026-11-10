import copy

ENGLISH_SECTION = 'Version anglaise (facultatif)'
ENGLISH_HELP = "Facultatif. Laissé vide, la page anglaise du site affiche la version française."


class SectionedFormMixin:
    """Regroupe les champs d'un formulaire en sections pour l'affichage.

    `sections` = ((titre, (noms de champs…)), …). Les champs absents (retirés selon les droits) sont ignorés,
    et un champ oublié dans `sections` est affiché à la fin : aucun champ ne disparaît silencieusement."""
    sections = ()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._prepare_english_fields()

    def _prepare_english_fields(self):
        """Champs « _en » (version anglaise) : retirés si le champ français n'est pas dans le formulaire, sinon
        facultatifs et affichés avec le même widget que le français (éditeur de texte riche compris)."""
        for name in [n for n in self.fields if n.endswith('_en')]:
            french = self.fields.get(name[:-3])
            if french is None:
                del self.fields[name]
                continue
            field = self.fields[name]
            field.required = False
            field.widget = copy.deepcopy(french.widget)
            field.widget.attrs.pop('required', None)
            field.widget.attrs.pop('placeholder', None)
            field.help_text = ENGLISH_HELP

    def grouped_fields(self):
        placed, groups = set(), []
        english = [n for n in self.fields if n.endswith('_en') and not self.fields[n].widget.is_hidden]
        placed.update(english)
        for title, names in self.sections:
            names = [n for n in names if n in self.fields and not self.fields[n].widget.is_hidden]
            placed.update(names)
            if names:
                groups.append((title, [self[n] for n in names]))
        if english:
            groups.append((ENGLISH_SECTION, [self[n] for n in english]))
        rest = [self[n] for n, f in self.fields.items() if n not in placed and not f.widget.is_hidden]
        if rest:
            groups.append(('Autres informations' if groups else '', rest))
        return groups

    def hidden_fields_list(self):
        return [self[n] for n, f in self.fields.items() if f.widget.is_hidden]
