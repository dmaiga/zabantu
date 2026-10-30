from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser
from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser
from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser
from django_summernote.widgets import SummernoteWidget, SummernoteInplaceWidget

from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from django.core.validators import RegexValidator
from .models import CustomUser

from django import forms
from django.contrib.auth.forms import UserChangeForm
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator

from django import forms
from site_web.models import NewsletterCampaign, NewsletterSubscriber, NewsletterRecipient
from django.utils import timezone
from django.db import models

# users/forms.py
from django import forms
from site_web.models import NewsletterCampaign, NewsletterSubscriber

CustomUser = get_user_model()


class CustomUserCreationForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'prenom', 'nom', 'role')
        
class LoginForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)


class CustomMemberCreationForm(forms.ModelForm):
    profile_picture = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={'accept': 'image/*'})
    )
    bio = forms.CharField(
        widget=SummernoteWidget(attrs={
            'summernote': {
                'width': '100%',
                'height': '300px',
                'toolbar': [
                    ['style', ['style']],
                    ['font', ['bold', 'italic', 'underline', 'clear']],
                    ['fontname', ['fontname']],
                    ['color', ['color']],
                    ['para', ['ul', 'ol', 'paragraph']],
                    ['table', ['table']],
                    ['insert', ['link', 'picture', 'video', 'hr']],
                    ['view', ['fullscreen', 'codeview', 'help']],
                ],
                'dialogsInBody': True,
                'dialogsFade': True,
                'disableDragAndDrop': False,
            }
        }),
        required=False,
        label="Bio"
    )

    class Meta:
        model = CustomUser
        fields = [
            'email', 'nom', 'prenom',
            'phone_number', 'profile_picture',
            'bio', 'job_title', 'department', 'date_started',
            'social_facebook', 'social_linkedin', 'social_twitter',
            'scholar_link','personal_website'
        ]
        widgets = {
            'date_started': forms.DateInput(attrs={'type': 'date'}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'membre'
        user.username = user.email
        user.set_unusable_password()
        
        # Attribuer l'image uploadée
        profile_picture = self.cleaned_data.get('profile_picture')
        if profile_picture:
            user.profile_picture = profile_picture
    
        if commit:
            user.save()
        return user



class ProfileEditForm(forms.ModelForm):
    
    
    phone_number = forms.CharField(
       
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': '+261 34 12 345 67'
        })
    )
    bio = forms.CharField(
        widget=SummernoteWidget(attrs={
            'summernote': {
                'width': '100%',
                'height': '300px',
                'toolbar': [
                    ['style', ['style']],
                    ['font', ['bold', 'italic', 'underline', 'clear']],
                    ['fontname', ['fontname']],
                    ['color', ['color']],
                    ['para', ['ul', 'ol', 'paragraph']],
                    ['table', ['table']],
                    ['insert', ['link', 'picture', 'video', 'hr']],
                    ['view', ['fullscreen', 'codeview', 'help']],
                ],
                'dialogsInBody': True,
                'dialogsFade': True,
                'disableDragAndDrop': False,
            }
        }),
        required=False,
        label="Bio"
    )
    class Meta:
        model = CustomUser
        fields = [
            'profile_picture',
            'nom',
            'prenom',
            'email',
            'phone_number',
            'job_title',
            'department',
            'bio',
            'social_facebook',
            'social_linkedin',
            'social_twitter',
            'social_instagram',
            
        ]
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4}),
        }

class CustomPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})


class CustomUserUpdateForm(UserChangeForm):
    
    
    phone_number = forms.CharField(
        label=_('Téléphone'),
        
        required=False,
        widget=forms.TextInput(attrs={'placeholder': '+22390423937'})
    )
    bio = forms.CharField(
        widget=SummernoteWidget(attrs={
            'summernote': {
                'width': '100%',
                'height': '500px',
                'toolbar': [
                    ['style', ['style']],
                    ['font', ['bold', 'italic', 'underline', 'clear']],
                    ['fontname', ['fontname']],
                    ['color', ['color']],
                    ['para', ['ul', 'ol', 'paragraph']],
                    ['table', ['table']],
                    ['insert', ['link', 'picture', 'video', 'hr']],
                    ['view', ['fullscreen', 'codeview', 'help']],
                ],
                'dialogsInBody': True,
                'dialogsFade': True,
                'disableDragAndDrop': False,
            }
        }),
        required=False,
        label="Bio"
    )
    
    password = None  # Nous gérons le mot de passe séparément
    
    class Meta:
        model = CustomUser
        fields = [
            'nom',
            'prenom',
            'email',
            'phone_number',
            'role',
            'is_active',
            'date_started',
            'profile_picture',
            'bio',
            'job_title',
            'department',
            'social_facebook',
            'social_linkedin',
            'social_twitter',
            'social_instagram',
              'scholar_link','personal_website'
        ]
        labels = {
            'is_active': _('Compte actif'),
            'date_started': _('Date de début'),
        }
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 3}),
            'date_started': forms.DateInput(attrs={'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Personnalisation des champs
        self.fields['email'].widget.attrs.update({'class': 'form-control'})
        self.fields['role'].widget.attrs.update({'class': 'form-select'})
        
        # Si l'utilisateur n'est pas admin, on restreint les champs modifiables
        if not self.instance.is_admin and not kwargs.get('initial', {}).get('is_admin', False):
            self.fields.pop('role')
            self.fields.pop('is_active')
            self.fields.pop('date_started')



class ContactReplyForm(forms.Form):
    reply_content = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 8,
            'class': 'form-control',
            'placeholder': 'Tapez votre réponse ici...'
        }),
        label='Votre réponse'
    )


class NewsletterCampaignForm(forms.ModelForm):
    subscribers = forms.ModelMultipleChoiceField(
        queryset=NewsletterSubscriber.objects.filter(is_active=True)
                       .order_by('email'),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'checkbox-select-multiple'}),
        required=False,
        label='Abonnés'
    )
    
    # Ajout d'un champ pour sélectionner tous les abonnés
    select_all = forms.BooleanField(
        required=False,
        label='Sélectionner tous les abonnés',
        widget=forms.CheckboxInput(attrs={'id': 'select-all'})
    )
    
    class Meta:
        model = NewsletterCampaign
        fields = ['title', 'subject', 'content', 'subscribers', 'select_all']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 10, 'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'subject': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            # Récupérer les abonnés déjà sélectionnés
            selected_subscribers = self.instance.recipients.values_list('subscriber_id', flat=True)
            self.fields['subscribers'].initial = selected_subscribers
    
    def save(self, commit=True):
        campaign = super().save(commit=False)
        
        if commit:
            campaign.save()
            
            # Mettre à jour les destinataires
            selected_subscribers = self.cleaned_data.get('subscribers', [])
            
            # Supprimer les anciennes relations
            campaign.recipients.all().delete()
            
            # Créer de nouvelles relations
            for subscriber in selected_subscribers:
                from site_web.models import NewsletterRecipient
                NewsletterRecipient.objects.create(campaign=campaign, subscriber=subscriber)
        
        return campaign
    


from django import forms
from .models import Partenaire


class PartenaireForm(forms.ModelForm):

    class Meta:
        model = Partenaire
        fields = ['name', 'logo','is_active', 'order']