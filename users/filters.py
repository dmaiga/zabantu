from django import forms
from django.db.models import Q

from .models import CustomUser


class MemberFilterForm(forms.Form):
    """Filtres de la liste des membres ; une valeur invalide est ignorée."""
    q = forms.CharField(required=False)
    role = forms.ChoiceField(required=False, choices=[c for c in CustomUser.ROLE_CHOICES if c[0] != 'admin'])
    access = forms.ChoiceField(required=False, choices=[('yes', 'Autorisée'), ('no', 'Sans accès')])

    def apply(self, queryset):
        self.is_valid()  # cleaned_data ne garde que les champs valides
        data = self.cleaned_data
        if data.get('q'):
            q = data['q']
            queryset = queryset.filter(
                Q(nom__icontains=q) | Q(prenom__icontains=q) | Q(email__icontains=q) | Q(department__icontains=q))
        if data.get('role'):
            queryset = queryset.filter(role=data['role'])
        can_log_in = Q(backoffice_access=True) | Q(role__in=['admin', 'moderateur']) | Q(is_superuser=True)
        if data.get('access') == 'yes':
            queryset = queryset.filter(can_log_in)
        elif data.get('access') == 'no':
            queryset = queryset.exclude(can_log_in)
        return queryset
