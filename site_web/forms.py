from django import forms


from django import forms
from .models import NewsletterSubscriber

class NewsletterForm(forms.ModelForm):
    class Meta:
        model = NewsletterSubscriber
        fields = ['email']
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'form-control form-control-lg',
                'placeholder': 'Votre email',
                'required': True,
            })
        }

# users/forms.py ou site_web/forms.py

from django import forms
from .models import ContactMessage, MembershipApplication
from django import forms
from .models import ContactMessage
from .antispam import AntiSpamMixin

class ContactForm(AntiSpamMixin, forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ['name', 'last_name', 'phone', 'email', 'subject', 'message']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Votre nom'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Votre prénom'}),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+223 XX XX XX XX',
                'pattern': r'^\+?[\d\s]{10,}$'
            }),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Votre email'}),
            'subject': forms.Select(attrs={'class': 'form-select'}, choices=[
                ('', 'Sélectionnez un sujet'),
                ('collaboration', 'Collaboration'),
                ('information', 'Demande d\'information'),
                ('other', 'Autre')
            ]),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Votre message'}),
        }
    
    # Ajouter des labels si nécessaire
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].label = "Nom"
        self.fields['last_name'].label = "Prénom"
        self.fields['phone'].label = "Téléphone"
        self.fields['email'].label = "Email"
        self.fields['subject'].label = "Sujet"
        self.fields['message'].label = "Message"



MAX_WORDS = 100
MAX_PHOTO_MB = 5


class MembershipApplicationForm(AntiSpamMixin, forms.ModelForm):
    how_heard_choices = forms.MultipleChoiceField(
        label="Comment avez-vous entendu parler de Zabantu ?",
        choices=MembershipApplication.HowHeard.choices,
        widget=forms.CheckboxSelectMultiple,
        error_messages={'required': "Sélectionnez au moins une réponse."},
    )

    class Meta:
        model = MembershipApplication
        fields = [
            'full_name', 'email', 'phone', 'city_country',
            'academic_status', 'institution',
            'research_interests',
            'how_heard_choices', 'how_heard', 'contribution', 'career_benefit',
            'profile_picture', 'bio',
            'social_linkedin', 'social_facebook', 'social_twitter', 'social_instagram',
            'scholar_link', 'personal_website',
            'consent',
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'autocomplete': 'email', 'inputmode': 'email'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+223 XX XX XX XX',
                                            'autocomplete': 'tel', 'inputmode': 'tel'}),
            'city_country': forms.TextInput(attrs={'class': 'form-control'}),
            'academic_status': forms.Select(attrs={'class': 'form-select'}),
            'institution': forms.TextInput(attrs={'class': 'form-control'}),
            'research_interests': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'how_heard': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Si « Autre », précisez'}),
            'contribution': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'data-max-words': MAX_WORDS}),
            'career_benefit': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'data-max-words': MAX_WORDS}),
            'profile_picture': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'social_linkedin': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://www.linkedin.com/in/…'}),
            'social_facebook': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://www.facebook.com/…'}),
            'social_twitter': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://x.com/…'}),
            'social_instagram': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://www.instagram.com/…'}),
            'scholar_link': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://scholar.google.com/…'}),
            'personal_website': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://…'}),
            'consent': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'contribution': "Comment souhaitez-vous contribuer aux activités de Zabantu ? (max 100 mots)",
            'career_benefit': "Comment adhérer à Zabantu peut-il vous aider à avancer dans votre carrière de chercheur(se) ? (max 100 mots)",
            'bio': "Courte biographie",
            'consent': ("J'autorise l'utilisation des informations fournies pour le traitement de ma demande "
                        "d'adhésion et la prise de contact avec moi."),
        }

    # Étape de l'assistant (wizard) à laquelle appartient chaque champ
    STEP_FIELDS = [
        ['full_name', 'email', 'phone', 'city_country'],
        ['academic_status', 'institution', 'research_interests'],
        ['how_heard_choices', 'how_heard', 'contribution', 'career_benefit'],
        ['profile_picture', 'bio', 'social_linkedin', 'social_facebook', 'social_twitter',
         'social_instagram', 'scholar_link', 'personal_website'],
        ['consent'],
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['academic_status'].choices = [('', 'Sélectionnez votre statut')] + list(
            MembershipApplication.AcademicStatus.choices)
        self.fields['consent'].required = True
        self.fields['consent'].error_messages['required'] = "Votre consentement est nécessaire pour traiter la demande."
        self.fields['how_heard'].required = False

    def first_error_step(self):
        """Index (0-based) de la première étape contenant une erreur, pour rouvrir le wizard dessus."""
        for index, names in enumerate(self.STEP_FIELDS):
            if any(name in self.errors for name in names):
                return index
        return 0

    def _clean_words(self, name):
        value = (self.cleaned_data.get(name) or '').strip()
        if len(value.split()) > MAX_WORDS:
            raise forms.ValidationError(f"Maximum {MAX_WORDS} mots.")
        return value

    def clean_contribution(self):
        return self._clean_words('contribution')

    def clean_career_benefit(self):
        return self._clean_words('career_benefit')

    def clean_profile_picture(self):
        photo = self.cleaned_data.get('profile_picture')
        if photo and photo.size > MAX_PHOTO_MB * 1024 * 1024:
            raise forms.ValidationError(f"La photo ne doit pas dépasser {MAX_PHOTO_MB} Mo.")
        return photo

    def clean(self):
        cleaned = super().clean()
        if 'autre' in (cleaned.get('how_heard_choices') or []) and not (cleaned.get('how_heard') or '').strip():
            self.add_error('how_heard', "Précisez votre réponse.")
        return cleaned


class NewsletterSubscribeForm(AntiSpamMixin, forms.Form):
    email = forms.EmailField(max_length=254)
