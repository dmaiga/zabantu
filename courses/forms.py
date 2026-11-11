from django import forms
from django.contrib.auth import authenticate, get_user_model, password_validation
from django.utils.translation import gettext_lazy as _

from site_web.antispam import AntiSpamMixin
from users.formsupport import SectionedFormMixin

from .backends import PARTICIPANT_ROLE
from .models import Cohort, Course, CourseFile, Enrollment, ParticipantProfile

User = get_user_model()
MAX_WORDS = 150


class SignupForm(AntiSpamMixin, forms.Form):
    """Création d'un compte participant. Le compte reste inactif jusqu'à la confirmation de l'adresse e-mail."""
    prenom = forms.CharField(label=_("Prénom"), max_length=100)
    nom = forms.CharField(label=_("Nom"), max_length=100)
    email = forms.EmailField(label=_("Adresse e-mail"))
    status = forms.ChoiceField(label=_("Vous êtes"), choices=ParticipantProfile.Status.choices)
    organization = forms.CharField(label=_("Organisation (université, entreprise, institution…)"), max_length=255,
                                   required=False)
    password1 = forms.CharField(label=_("Mot de passe"), strip=False, widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}))
    password2 = forms.CharField(label=_("Confirmez le mot de passe"), strip=False,
                                widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}))
    consent = forms.BooleanField(label=_("J'accepte que mes informations servent à gérer mon compte et mes inscriptions aux formations."),
                                 error_messages={'required': _("Votre accord est nécessaire pour créer le compte.")})

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['status'].choices = [('', _('Sélectionnez votre profil'))] + list(ParticipantProfile.Status.choices)
        attrs = {'prenom': 'given-name', 'nom': 'family-name', 'email': 'email', 'organization': 'organization'}
        for name, field in self.fields.items():
            css = 'form-check-input' if name == 'consent' else 'form-select' if name == 'status' else 'form-control'
            field.widget.attrs.setdefault('class', css)
            if name in attrs:
                field.widget.attrs['autocomplete'] = attrs[name]

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists() or User.objects.filter(username__iexact=email).exists():
            raise forms.ValidationError(_("Un compte existe déjà avec cette adresse. Connectez-vous ou utilisez « Mot de passe oublié »."))
        return email

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get('password1'), cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', _("Les deux mots de passe ne correspondent pas."))
        elif p1:
            user = User(username=cleaned.get('email', ''), email=cleaned.get('email', ''),
                        prenom=cleaned.get('prenom', ''), nom=cleaned.get('nom', ''))
            try:
                password_validation.validate_password(p1, user)
            except forms.ValidationError as error:
                self.add_error('password1', error)
        return cleaned

    def save(self, language='fr'):
        data = self.cleaned_data
        user = User(username=data['email'], email=data['email'], prenom=data['prenom'], nom=data['nom'],
                    first_name=data['prenom'], last_name=data['nom'], role=PARTICIPANT_ROLE, is_active=False)
        user.set_password(data['password1'])
        user.save()
        ParticipantProfile.objects.create(user=user, status=data['status'], organization=data['organization'],
                                          language=language)
        return user


class SiteLoginForm(forms.Form):
    """Connexion unique pour tout le monde (équipe et participants) : e-mail ou identifiant, puis mot de passe.
    L'aiguillage (backoffice ou espace participant) se fait après la connexion, côté serveur."""
    identifier = forms.CharField(label=_("Adresse e-mail ou identifiant"), max_length=254,
                                 widget=forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'username',
                                                               'autocapitalize': 'none', 'autofocus': True}))
    password = forms.CharField(label=_("Mot de passe"), strip=False,
                               widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'current-password'}))

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user = None
        super().__init__(*args, **kwargs)

    def clean(self):
        from django.db.models import Q
        cleaned = super().clean()
        identifier, password = (cleaned.get('identifier') or '').strip(), cleaned.get('password')
        if identifier and password:
            account = User.objects.filter(Q(username__iexact=identifier) | Q(email__iexact=identifier)).first()
            if account is not None:
                self.user = authenticate(self.request, username=account.username, password=password)
            if self.user is None:
                if account is not None and account.check_password(password):
                    if not account.is_active and account.role == PARTICIPANT_ROLE:
                        raise forms.ValidationError(
                            _("Votre adresse n'est pas encore confirmée : ouvrez le lien reçu par e-mail."), code='inactive')
                    raise forms.ValidationError(
                        _("Ce compte ne permet pas de se connecter. Contactez l'équipe Zabantu si besoin."), code='no_access')
                raise forms.ValidationError(_("Identifiant ou mot de passe incorrect."), code='invalid')
        return cleaned


def _count_words(value):
    return len((value or '').split())


class EnrollmentForm(forms.ModelForm):
    class Meta:
        model = Enrollment
        fields = ['motivation', 'expectations']
        widgets = {
            'motivation': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'data-max-words': MAX_WORDS}),
            'expectations': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'data-max-words': MAX_WORDS}),
        }

    def _limit(self, name):
        value = (self.cleaned_data.get(name) or '').strip()
        if _count_words(value) > MAX_WORDS:
            raise forms.ValidationError(_("Maximum %(n)s mots.") % {'n': MAX_WORDS})
        return value

    def clean_motivation(self):
        return self._limit('motivation')

    def clean_expectations(self):
        return self._limit('expectations')


class ParticipantProfileForm(forms.ModelForm):
    """Profil modifiable dans l'espace participant : identité (compte) et profil (formations)."""
    prenom = forms.CharField(label=_("Prénom"), max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    nom = forms.CharField(label=_("Nom"), max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))

    class Meta:
        model = ParticipantProfile
        fields = ['status', 'organization', 'notify_cohorts']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'organization': forms.TextInput(attrs={'class': 'form-control'}),
            'notify_cohorts': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = self.instance.user
        self.fields['prenom'].initial, self.fields['nom'].initial = user.prenom, user.nom
        self.order_fields(['prenom', 'nom', 'status', 'organization', 'notify_cohorts'])

    def save(self, commit=True):
        profile = super().save(commit)
        user = profile.user
        user.prenom = user.first_name = self.cleaned_data['prenom']
        user.nom = user.last_name = self.cleaned_data['nom']
        user.save(update_fields=['prenom', 'nom', 'first_name', 'last_name'])
        return profile


class MembershipLightForm(forms.Form):
    """Demande d'adhésion depuis l'espace participant : nom, e-mail et profil sont déjà connus."""
    city_country = forms.CharField(label=_("Ville et pays de résidence"), max_length=255,
                                   widget=forms.TextInput(attrs={'class': 'form-control'}))
    institution = forms.CharField(label=_("Institution d'affiliation"), max_length=255,
                                  widget=forms.TextInput(attrs={'class': 'form-control'}))
    phone = forms.CharField(label=_("Téléphone (WhatsApp, si disponible)"), max_length=30, required=False,
                            widget=forms.TextInput(attrs={'class': 'form-control', 'inputmode': 'tel'}))
    research_interests = forms.CharField(label=_("Principaux centres de recherche"),
                                         widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}))
    contribution = forms.CharField(label=_("Comment souhaitez-vous contribuer aux activités de Zabantu ? (max 100 mots)"),
                                   widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4}))
    consent = forms.BooleanField(label=_("J'autorise l'utilisation des informations fournies pour le traitement de ma demande d'adhésion et la prise de contact avec moi."),
                                 widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
                                 error_messages={'required': _("Votre consentement est nécessaire pour traiter la demande.")})

    def clean_contribution(self):
        value = self.cleaned_data['contribution'].strip()
        if _count_words(value) > 100:
            raise forms.ValidationError(_("Maximum %(n)s mots.") % {'n': 100})
        return value

    def save(self, user, language):
        from site_web.models import MembershipApplication
        profile = user.participant_profile
        data = self.cleaned_data
        return MembershipApplication.objects.create(
            full_name=user.get_full_name(), email=user.email, phone=data['phone'], city_country=data['city_country'],
            academic_status=profile.status, institution=data['institution'],
            research_interests=data['research_interests'], contribution=data['contribution'], career_benefit='',
            how_heard_choices=['autre'], how_heard="Compte participant (formations)", consent=True, language=language)


# ----- Backoffice (en français) -----

class CourseForm(SectionedFormMixin, forms.ModelForm):
    sections = (('Cours', ('title', 'summary')),)

    class Meta:
        model = Course
        fields = ['title', 'summary', 'title_en', 'summary_en']
        widgets = {'summary': forms.Textarea(attrs={'rows': 6})}
        help_texts = {'summary': "Présentation affichée aux participants : objectifs, contenu, public visé."}


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('widget', MultipleFileInput(attrs={'class': 'form-control'}))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single = super().clean
        if isinstance(data, (list, tuple)):
            return [single(item, initial) for item in data]
        return [single(data, initial)] if data else []


class CourseFilesForm(forms.Form):
    """Ajout de plusieurs fichiers d'un coup ; chacun est contrôlé (format, poids)."""
    files = MultipleFileField(label="Fichiers", help_text="PDF, Word, PowerPoint, Excel, OpenDocument, ZIP, texte ; 50 Mo au plus par fichier.")

    def clean_files(self):
        from .models import validate_course_file
        files = self.cleaned_data['files']
        for upload in files:
            try:
                validate_course_file(upload)
            except forms.ValidationError as error:
                raise forms.ValidationError(f"{upload.name} : {error.messages[0]}")
        return files


class CourseFileTitleForm(forms.ModelForm):
    class Meta:
        model = CourseFile
        fields = ['title', 'order']


class CohortForm(SectionedFormMixin, forms.ModelForm):
    sections = (
        ('Cohorte', ('name', 'description')),
        ('Inscriptions', ('opens_on', 'closes_on')),
        ('Cours', ('courses',)),
    )

    class Meta:
        model = Cohort
        fields = ['name', 'description', 'opens_on', 'closes_on', 'courses', 'name_en', 'description_en']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
            'opens_on': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'closes_on': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'courses': forms.CheckboxSelectMultiple,
        }
        help_texts = {
            'opens_on': "Dès ce jour, la cohorte apparaît sur la page « Formations » et les participants sont prévenus par e-mail.",
            'closes_on': "Dernier jour pour s'inscrire.",
            'courses': "Cours que les participants acceptés pourront consulter.",
        }
