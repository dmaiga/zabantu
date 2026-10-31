from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator
from django.urls import reverse

class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('admin', _('Administrateur')),
        ('moderateur', _('Modérateur')),
        ('membre', _('Membre')),
    ]
    
    
    # Identité
    nom = models.CharField(_('nom'), max_length=100, blank=False)
    prenom = models.CharField(_('prénom'), max_length=100, blank=False)
    
    # Rôle et statut
    role = models.CharField(
        _('rôle'), 
        max_length=20, 
        choices=ROLE_CHOICES, 
        default='membre'
    )
    date_started = models.DateField(_('date de début'), null=True, blank=True)
    is_active = models.BooleanField(_('actif'), default=True)
    backoffice_access = models.BooleanField(
        _('accès au backoffice'), default=False,
        help_text=_("Autorise ce membre à se connecter. Les administrateurs et modérateurs se connectent toujours."))
    
    # Contact
    email = models.EmailField(_('email'), unique=True, blank=False)
    
    phone_number = models.CharField(max_length=20, blank=True, null=True, verbose_name="Téléphone")
    
    # Dans users/models.py
    profile_picture = models.ImageField(
    _('photo de profil'),
    upload_to='profiles/',  
    blank=True,
    default=None 
        )
    
    # Profession
    bio = models.TextField(_('biographie'), blank=True, null=True)
    job_title = models.CharField(_('poste'), max_length=100, blank=True, null=True)
    department = models.CharField(_('département'), max_length=100, blank=True, null=True)
    
    # Réseaux sociaux
    social_facebook = models.URLField(_('Facebook'), blank=True, null=True)
    social_linkedin = models.URLField(_('LinkedIn'), blank=True, null=True)
    social_twitter = models.URLField(_('Twitter'), blank=True, null=True)
    social_instagram = models.URLField(_('Instagram'), blank=True, null=True)
    #Liens académiques et personnels
    scholar_link = models.URLField(
        _('Google Scholar'),
        blank=True, 
        null=True,
        help_text=_("Lien vers votre profil Google Scholar")
    )
    
    personal_website = models.URLField(
        _('Site web personnel'),
        blank=True, 
        null=True,
        help_text=_("Lien vers votre site web personnel ou portfolio")
    )
    # Métadonnées
    created_at = models.DateTimeField(_('créé le'), auto_now_add=True)
    updated_at = models.DateTimeField(_('modifié le'), auto_now=True)
    
    class Meta:
        verbose_name = _('utilisateur')
        verbose_name_plural = _('utilisateurs')
        ordering = ['nom', 'prenom']
    
    REQUIRED_FIELDS = ['nom', 'prenom', 'email']
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.get_role_display()})"
    
    def get_full_name(self):
        """Retourne le nom complet."""
        return f"{self.prenom} {self.nom}".strip()
    
    def get_short_name(self):
        """Retourne le prénom."""
        return self.prenom
    
    def get_profile_picture(self):
        """Retourne l'URL de la photo de profil ou une image par défaut."""
        if self.profile_picture:
            return self.profile_picture.url
        return '/static/images/default-profile.png'
    
    def get_social_links(self):
        """Retourne les liens sociaux sous forme de dictionnaire."""
        return {
            'facebook': self.social_facebook,
            'linkedin': self.social_linkedin,
            'twitter': self.social_twitter,
            'instagram': self.social_instagram,
            'scholar': self.scholar_link,
            'website': self.personal_website
        }
    
    def get_public_profile(self):
        """Retourne l'URL publique du profil du membre."""
        return reverse('public_member_detail', args=[self.pk])
    
    @property
    def is_admin(self):
        return self.role == 'admin'
    
    @property
    def is_moderator(self):
        return self.role == 'moderateur'

    @property
    def can_access_backoffice(self):
        """Seuls les administrateurs, les modérateurs et les membres explicitement autorisés peuvent se connecter."""
        return self.is_superuser or self.role in ('admin', 'moderateur') or self.backoffice_access

    @property
    def can_moderate(self):
        """Peut publier, dépublier et supprimer les contenus du site."""
        return self.is_superuser or self.role in ('admin', 'moderateur')
    
    @property
    def has_academic_profile(self):
        """Vérifie si l'utilisateur a un profil académique."""
        return bool(self.scholar_link)
    
    @property
    def has_personal_website(self):
        """Vérifie si l'utilisateur a un site web personnel."""
        return bool(self.personal_website)
    
    def save(self, *args, **kwargs):
        # Nettoyage des champs
        self.email = self.email.lower().strip()
        self.nom = self.nom.strip().upper()
        self.prenom = self.prenom.strip().title()
        # Un superutilisateur (createsuperuser) reçoit le rôle admin par défaut,
        # sinon les vues réservées aux admin/modérateurs le rejettent.
        if self.is_superuser and self.role == 'membre':
            self.role = 'admin'
        super().save(*args, **kwargs)


from django.db import models


class Partenaire(models.Model):
    name = models.CharField(max_length=255)
    logo = models.ImageField(upload_to='partenaires/')
   

    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return self.name