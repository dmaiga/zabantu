from django import forms
from django.db.models import Q
from django.utils import timezone

from .models import Event


class EventFilterForm(forms.Form):
    """Filtres de la liste des événements ; une valeur invalide est ignorée."""
    q = forms.CharField(required=False)
    type = forms.ChoiceField(required=False, choices=Event.EVENT_TYPE_CHOICES)
    status = forms.ChoiceField(required=False, choices=Event.STATUS_CHOICES)
    when = forms.ChoiceField(required=False, choices=[('upcoming', 'À venir'), ('past', 'Passés')])
    sort = forms.ChoiceField(required=False, choices=[('-date', 'Plus récents d\'abord'), ('date', 'Plus anciens d\'abord')])

    SEARCH_FIELDS = ('title', 'content', 'location', 'primary_topic')

    def apply(self, queryset):
        self.is_valid()  # cleaned_data ne garde que les champs valides
        data = self.cleaned_data
        if data.get('q'):
            query = Q()
            for field in self.SEARCH_FIELDS:
                query |= Q(**{f'{field}__icontains': data['q']})
            queryset = queryset.filter(query)
        if data.get('type'):
            queryset = queryset.filter(event_type=data['type'])
        if data.get('status'):
            queryset = queryset.filter(status=data['status'])
        if data.get('when') == 'upcoming':
            queryset = queryset.filter(date__gte=timezone.now())
        elif data.get('when') == 'past':
            queryset = queryset.filter(date__lt=timezone.now())
        return queryset.order_by(data.get('sort') or '-date')
