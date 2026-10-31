from django import forms
from django.db.models import Q

from .models import Intervenant


class IntervenantFilterForm(forms.Form):
    """Filtres de la liste des intervenants ; une valeur invalide est ignorée."""
    q = forms.CharField(required=False)
    type = forms.ChoiceField(required=False, choices=Intervenant.TYPE_INTERVENANT_CHOICES)
    availability = forms.ChoiceField(required=False, choices=[('available', 'Disponibles'), ('unavailable', 'Indisponibles')])

    SEARCH_FIELDS = ('first_name', 'last_name', 'organization', 'expertise')

    def apply(self, queryset):
        self.is_valid()  # cleaned_data ne garde que les champs valides
        data = self.cleaned_data
        if data.get('q'):
            query = Q()
            for field in self.SEARCH_FIELDS:
                query |= Q(**{f'{field}__icontains': data['q']})
            queryset = queryset.filter(query)
        if data.get('type'):
            queryset = queryset.filter(intervenant_type=data['type'])
        if data.get('availability'):
            queryset = queryset.filter(is_available=data['availability'] == 'available')
        return queryset
