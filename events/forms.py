from django import forms
from django.utils import timezone
from .models import Event,EventIntervenant
from intervenants.models import Intervenant

class EventForm(forms.ModelForm):
    
    # Champ personnalisé pour le lien de webinaire
    webinar_link_raw = forms.CharField(
        required=False,
        label="Lien du webinaire",
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'teams.microsoft.com/l/meetup-join/...'
        })
    )
    
    class Meta:
        model = Event
        fields = [
            'title', 'event_type', 'content', 'image', 
            'date', 'end_date', 'location', 'lieu_gps',
            'is_webinar', 'is_featured',  # Retirer is_published
            'target_audience', 'expected_attendees', 
            'primary_topic', 'secondary_topics'
        ]
        widgets = {
            'date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'end_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'content': forms.Textarea(attrs={'rows': 4, 'class': 'form-control '}),  # Caché, géré par Summernote
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'event_type': forms.Select(attrs={'class': 'form-select'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'lieu_gps': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://goo.gl/maps/...'}),
            'target_audience': forms.TextInput(attrs={'class': 'form-control'}),
            'expected_attendees': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'primary_topic': forms.TextInput(attrs={'class': 'form-control'}),
            'secondary_topics': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Séparés par des virgules'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_webinar': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'is_featured': 'Mettre en avant (à la une)',
            'is_webinar': 'Événement en ligne',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Pré-selectionner les intervenants si l'événement existe
        if self.instance and self.instance.pk:
           
            # Pré-remplir le champ raw si un lien existe
            if self.instance.webinar_link:
                # Enlever le préfixe http:// pour l'affichage
                link = self.instance.webinar_link
                if link.startswith(('http://', 'https://')):
                    link = link.split('://', 1)[1]
                self.fields['webinar_link_raw'].initial = link
        
        # Masquer le champ de statut dans le formulaire standard
        # Le statut est géré par des actions spécifiques (publish/unpublish/archive)
    
    def clean_webinar_link_raw(self):
        """Valider et formater le lien de webinaire"""
        raw_link = self.cleaned_data.get('webinar_link_raw', '').strip()
        
        if not raw_link:
            return ''
        
        # Ajouter https:// si manquant
        if not raw_link.startswith(('http://', 'https://')):
            raw_link = 'https://' + raw_link
        
        # Validation basique d'URL
        if ' ' in raw_link:
            raise forms.ValidationError("Le lien ne doit pas contenir d'espaces")
        
        return raw_link
    
    def clean(self):
        cleaned_data = super().clean()
        date = cleaned_data.get('date')
        end_date = cleaned_data.get('end_date')
        is_webinar = cleaned_data.get('is_webinar')
        webinar_link_raw = cleaned_data.get('webinar_link_raw')
        location = cleaned_data.get('location')
        
        # Validation de la date
        if date and date < timezone.now():
            raise forms.ValidationError("La date de l'événement ne peut pas être dans le passé")
        
        if end_date and date and end_date < date:
            raise forms.ValidationError("La date de fin ne peut pas être avant la date de début")
        
        # Validation des champs conditionnels
        if is_webinar and not webinar_link_raw:
            raise forms.ValidationError("Un lien de webinaire est requis pour les événements en ligne")
        
        if not is_webinar and not location:
            raise forms.ValidationError("Un lieu est requis pour les événements en présentiel")
        
        # Validation du nombre d'attendues
        expected_attendees = cleaned_data.get('expected_attendees')
        if expected_attendees is not None and expected_attendees < 0:
            raise forms.ValidationError("Le nombre attendu de participants ne peut pas être négatif")
        
        # Mettre à jour le champ webinar_link avec la valeur formatée
        if webinar_link_raw:
            cleaned_data['webinar_link'] = webinar_link_raw
        
        return cleaned_data
    
    def save(self, commit=True):
        event = super().save(commit=False)
        
        # Sauvegarder le lien formaté
        webinar_link_raw = self.cleaned_data.get('webinar_link_raw')
        if webinar_link_raw:
            event.webinar_link = webinar_link_raw
        
        # Toujours créer en mode brouillon (sécurité)
        if not event.pk:
            event.status = 'draft'
        
        if commit:
            event.save()
            # Sauvegarder les relations many-to-many
            self.save_m2m()
        

        return event
    

class EventIntervenantForm(forms.ModelForm):
    class Meta:
        model = EventIntervenant
        fields = ['intervenant', 'role']

        widgets = {
            'intervenant': forms.Select(attrs={'class': 'form-select'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
        }