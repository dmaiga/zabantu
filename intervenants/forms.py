from django import forms
from users.formsupport import SectionedFormMixin
from .models import Intervenant
import re

class IntervenantForm(SectionedFormMixin, forms.ModelForm):
    sections = (
        ('Identité', ('first_name', 'last_name', 'email', 'phone', 'photo')),
        ('Profil', ('organization', 'position', 'intervenant_type', 'expertise', 'bio')),
        ('Liens', ('linkedin', 'facebook', 'website')),
        ('Disponibilité et notes', ('is_available', 'note_internal')),
    )
    class Meta:
        model = Intervenant
        fields = [
            'first_name', 'last_name', 'email', 'phone',
            'organization', 'position', 'intervenant_type',
            'bio', 'expertise', 'photo',
            'linkedin', 'facebook', 'website',
            'is_available', 'note_internal'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Prénom'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@exemple.com'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+223 XXXXXXXX'}),
            'organization': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom de l\'organisation'}),
            'position': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Poste occupé'}),
            'intervenant_type': forms.Select(attrs={'class': 'form-select'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Biographie professionnelle...'}),
            'expertise': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Domaines d\'expertise séparés par des virgules'}),
            'linkedin': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'linkedin.com/in/nom-utilisateur'}),
            'facebook': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'facebook.com/nom-utilisateur'}),
            'website': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'votre-site.com'}),
            'note_internal': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Notes internes...'}),
            'is_available': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'first_name': "Prénom",
            'last_name': "Nom",
            'intervenant_type': "Type d'intervenant",
            'is_available': "Disponible pour de nouveaux événements",
            'note_internal': "Notes internes"
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Rendre le champ email obligatoire seulement à la création
        if not self.instance.pk:
            self.fields['email'].required = True
        
        # Modifier les placeholders pour indiquer que https:// est optionnel
        self.fields['linkedin'].widget.attrs['placeholder'] = 'linkedin.com/in/nom-utilisateur (https:// optionnel)'
        self.fields['facebook'].widget.attrs['placeholder'] = 'facebook.com/nom-utilisateur (https:// optionnel)'
        self.fields['website'].widget.attrs['placeholder'] = 'votre-site.com (https:// optionnel)'
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            # Vérifier l'unicité de l'email (sauf pour l'instance actuelle)
            queryset = Intervenant.objects.filter(email=email)
            if self.instance and self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            
            if queryset.exists():
                raise forms.ValidationError("Un intervenant avec cet email existe déjà.")
        return email
    
    def clean_linkedin(self):
        linkedin = self.cleaned_data.get('linkedin')
        return self._normalize_url(linkedin, 'linkedin.com')
    
    def clean_facebook(self):
        facebook = self.cleaned_data.get('facebook')
        return self._normalize_url(facebook, 'facebook.com')
    
    def clean_website(self):
        website = self.cleaned_data.get('website')
        return self._normalize_url(website)
    
    def _normalize_url(self, url, expected_domain=None):
        """
        Normalise une URL en ajoutant https:// si nécessaire
        et vérifie le domaine si spécifié
        """
        if not url:
            return url
        
        # Supprimer les espaces et slashs en début/fin
        url = url.strip().strip('/')
        
        # Si l'URL ne commence pas par http:// ou https://, ajouter https://
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # Vérifier le domaine si spécifié
        if expected_domain:
            # Extraire le domaine de l'URL
            domain_match = re.search(r'https?://([^/]+)', url)
            if domain_match:
                domain = domain_match.group(1)
                # Vérifier si le domaine correspond à celui attendu
                if expected_domain not in domain:
                    raise forms.ValidationError(
                        f"L'URL doit appartenir au domaine {expected_domain}. "
                        f"Exemple: https://{expected_domain}/nom-utilisateur"
                    )
        
        return url