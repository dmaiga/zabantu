class SectionedFormMixin:
    """Regroupe les champs d'un formulaire en sections pour l'affichage.

    `sections` = ((titre, (noms de champs…)), …). Les champs absents (retirés selon les droits) sont ignorés,
    et un champ oublié dans `sections` est affiché à la fin : aucun champ ne disparaît silencieusement."""
    sections = ()

    def grouped_fields(self):
        placed, groups = set(), []
        for title, names in self.sections:
            names = [n for n in names if n in self.fields and not self.fields[n].widget.is_hidden]
            placed.update(names)
            if names:
                groups.append((title, [self[n] for n in names]))
        rest = [self[n] for n, f in self.fields.items() if n not in placed and not f.widget.is_hidden]
        if rest:
            groups.append(('Autres informations' if groups else '', rest))
        return groups

    def hidden_fields_list(self):
        return [self[n] for n, f in self.fields.items() if f.widget.is_hidden]
