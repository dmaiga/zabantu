from django import forms
from django.db.models import Q

from .models import Article, Guelekan


class ArticleFilterForm(forms.Form):
    """Filtres de la liste des publications ; une valeur invalide est simplement ignorée."""
    q = forms.CharField(required=False)
    type = forms.ChoiceField(required=False, choices=Article.TYPE_MENU)
    status = forms.ChoiceField(required=False, choices=Article.STATUS_CHOICES)
    date_from = forms.DateField(required=False)
    date_to = forms.DateField(required=False)

    LOOKUPS = (
        ('type', 'article_type'),
        ('status', 'status'),
        ('date_from', 'created_at__date__gte'),
        ('date_to', 'created_at__date__lte'),
    )
    SEARCH_FIELDS = ('title', 'subtitle', 'content')

    def apply(self, queryset):
        self.is_valid()  # cleaned_data ne garde que les champs valides
        data = self.cleaned_data
        if data.get('q'):
            query = Q()
            for field in self.SEARCH_FIELDS:
                query |= Q(**{f'{field}__icontains': data['q']})
            queryset = queryset.filter(query)
        for name, lookup in self.LOOKUPS:
            if data.get(name):
                queryset = queryset.filter(**{lookup: data[name]})
        return queryset


class GuelekanFilterForm(ArticleFilterForm):
    """Même logique pour les Gɛlɛkan : recherche et statut."""
    status = forms.ChoiceField(required=False, choices=Guelekan.STATUS_CHOICES)
    LOOKUPS = (('status', 'status'),)
    SEARCH_FIELDS = ('title', 'subtitle')
    type = date_from = date_to = None
