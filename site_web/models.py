import os
from django.core.files.base import ContentFile
from django.utils.html import escape
from django.utils.html import linebreaks
from django.db import models
from django.utils.translation import gettext_lazy as _
from ckeditor.fields import RichTextField
import uuid
from django.utils import timezone
from django.db import models
from django.utils import timezone
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
User = get_user_model()
from zabantu import settings
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
from django.template.loader import render_to_string

class NewsletterSubscriber(models.Model):
    email = models.EmailField(_('email'), unique=True)
    subscribed_at = models.DateTimeField(_('date d\'inscription'), auto_now_add=True)
    is_active = models.BooleanField(_('actif'), default=True)
    token = models.UUIDField(_('token de désinscription'), default=uuid.uuid4, editable=False, unique=True)

    def __str__(self):
        return self.email

    class Meta:
        verbose_name = _("abonné à l'info-lettre")
        verbose_name_plural = _("abonnés à l'info-lettre")

class NewsletterCampaign(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Brouillon'),
        ('sending', 'En cours d\'envoi'),
        ('sent', 'Envoyé'),
        ('partial', 'Partiellement envoyé'),
        ('failed', 'Échec d\'envoi'),       
        ('cancelled', 'Annulé'),
    )
    
    title = models.CharField(_('titre'), max_length=200)
    subject = models.CharField(_('sujet'), max_length=200)
    content = models.TextField(_('contenu'))
    status = models.CharField(_('statut'), max_length=20, choices=STATUS_CHOICES, default='draft')
    sent_at = models.DateTimeField(_('envoyé le'), null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name=_('créé par'))
    created_at = models.DateTimeField(_('créé le'), auto_now_add=True)
    updated_at = models.DateTimeField(_('mis à jour le'), auto_now=True)
    
    # Pour lier à un contenu spécifique (article, événement, etc.)
    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    class Meta:
        verbose_name = _("campagne d'info-lettre")
        verbose_name_plural = _("campagnes d'info-lettre")
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
    
    def get_recipients_count(self):
        return self.recipients.count()
    
    def send(self):
        """Envoie la campagne aux destinataires encore abonnés ; renvoie (envoyés, échecs)."""
        from .mailing import send_campaign
        return send_campaign(self)

    class Meta:
        verbose_name = _("campagne d'info-lettre")
        verbose_name_plural = _("campagnes d'info-lettre")
        ordering = ['-created_at']


class NewsletterLog(models.Model):
    campaign = models.ForeignKey(NewsletterCampaign, on_delete=models.CASCADE, verbose_name=_('campagne'))
    subscriber = models.ForeignKey(NewsletterSubscriber, on_delete=models.CASCADE, verbose_name=_('abonné'))
    sent_at = models.DateTimeField(_('envoyé le'), auto_now_add=True)
    opened_at = models.DateTimeField(_('ouvert le'), null=True, blank=True)
    is_opened = models.BooleanField(_('ouvert'), default=False)
    token = models.UUIDField(_('token de suivi'), default=uuid.uuid4, editable=False, unique=True)
    
    class Meta:
        verbose_name = _("journal d'info-lettre")
        verbose_name_plural = _("journaux d'info-lettre")
        unique_together = ('campaign', 'subscriber')

class NewsletterRecipient(models.Model):
    campaign = models.ForeignKey(NewsletterCampaign, on_delete=models.CASCADE, related_name='recipients')
    subscriber = models.ForeignKey('site_web.NewsletterSubscriber', on_delete=models.CASCADE)
    sent_at = models.DateTimeField(_('envoyé le'), null=True, blank=True)
    opened_at = models.DateTimeField(_('ouvert le'), null=True, blank=True)
    attempts = models.PositiveSmallIntegerField(_('tentatives'), default=0)
    last_error = models.CharField(_('dernière erreur'), max_length=255, blank=True)

    class Meta:
        verbose_name = _("destinataire d'info-lettre")
        verbose_name_plural = _("destinataires d'info-lettre")
        unique_together = ['campaign', 'subscriber']
                             

class ContactMessage(models.Model):
    class Status(models.TextChoices):
        NEW = 'new', 'Nouveau'
        READ = 'read', 'Lu'
        REPLIED = 'replied', 'Répondu'
        ARCHIVED = 'archived', 'Archivé'

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.NEW
    )
    name = models.CharField("Nom", max_length=255)
    last_name = models.CharField("Prénom", max_length=255)
    phone = models.CharField(
        "Téléphone",
        max_length=20,
        blank=True,
        help_text="Format : +223 XX XXX XXX ou 00223XXXXXXXX"
    )
    email = models.EmailField("Email")
    subject = models.CharField("Sujet", max_length=255)
    message = models.TextField("Message")
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField("Lu", default=False)
    replied = models.BooleanField("Répondu", default=False)
    replied_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Répondu par",
        related_name="replied_messages"
    )
    replied_at = models.DateTimeField("Date de réponse", null=True, blank=True)
    # Ajoutez ces champs si vous voulez suivre l'IP et le user agent
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Message de contact"
        verbose_name_plural = "Messages de contact"
    
    def __str__(self):
        return f"{self.name} - {self.subject}"
    # models.py
    def add_response(self, user, response_content):
        response = MessageResponse.objects.create(
            contact_message=self,
            responded_by=user,
            response_content=response_content
        )
        self.status = self.Status.REPLIED
        self.replied = True
        self.save()
        return response
    
    @property
    def full_name(self):
        return f"{self.name} {self.last_name}"
    

class MessageResponse(models.Model):
    contact_message = models.ForeignKey(
        ContactMessage, 
        on_delete=models.CASCADE, 
        related_name="responses"
    )
    responded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Répondu par"
    )
    response_content = models.TextField("Contenu de la réponse")
    email_sent = models.BooleanField("Email envoyé", default=False)
    sent_at = models.DateTimeField("Envoyé le", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Réponse"
        verbose_name_plural = "Réponses"

    def __str__(self):
        return f"Réponse à {self.contact_message} par {self.responded_by}"

class MembershipApplication(models.Model):
    """Demande d'adhésion en ligne au groupe de recherche Zabantu."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'En attente'
        APPROVED = 'approved', 'Validée'
        REJECTED = 'rejected', 'Refusée'
        REVOKED = 'revoked', 'Révoquée'

    class AcademicStatus(models.TextChoices):
        BACHELOR = 'licence', 'Étudiant(e) en licence'
        MASTER = 'master', 'Étudiant(e) en master'
        PHD = 'doctorant', 'Doctorant(e)'
        TEACHER_RESEARCHER = 'enseignant_chercheur', 'Enseignant(e)-chercheur(e)'
        RESEARCHER = 'chercheur', 'Chercheur(e)'
        PROFESSIONAL = 'professionnel', 'Professionnel(le)'
        OTHER = 'autre', 'Autre'

    class HowHeard(models.TextChoices):
        COLLEAGUE = 'collegue', 'Un(e) collègue ou un(e) ami(e)'
        SOCIAL = 'reseaux_sociaux', 'Les réseaux sociaux'
        WEBSITE = 'site_web', 'Le site web de Zabantu'
        EVENT = 'evenement', 'Un événement ou un séminaire (Gɛlɛkan)'
        PUBLICATION = 'publication', 'Une publication de Zabantu'
        NEWSLETTER = 'newsletter', 'La newsletter'
        OTHER = 'autre', 'Autre'

    # 1. Informations personnelles
    full_name = models.CharField("Nom et prénom(s)", max_length=255)
    email = models.EmailField("Adresse e-mail")
    phone = models.CharField("Téléphone (WhatsApp, si disponible)", max_length=30, blank=True)
    city_country = models.CharField("Ville et pays de résidence", max_length=255)

    # 2. Profil académique ou professionnel
    academic_status = models.CharField("Statut", max_length=30, choices=AcademicStatus.choices)
    institution = models.CharField("Institution d'affiliation", max_length=255)

    # 3. Centres d'intérêt scientifiques
    research_interests = models.TextField("Principaux centres de recherche")

    # 4. Adhésion au groupe
    how_heard_choices = models.JSONField("Comment avez-vous entendu parler de Zabantu ?", default=list)
    how_heard = models.TextField("Autre (précisez)", blank=True)
    contribution = models.TextField("Contribution aux activités de Zabantu")
    career_benefit = models.TextField("Apport de l'adhésion pour votre carrière")

    # Profil public (facultatif) : recopié sur le compte membre à la validation
    profile_picture = models.ImageField("Photo de profil", upload_to='membership/photos/', blank=True)
    bio = models.TextField("Courte biographie", blank=True)
    social_linkedin = models.URLField("LinkedIn", blank=True)
    social_facebook = models.URLField("Facebook", blank=True)
    social_twitter = models.URLField("Twitter / X", blank=True)
    social_instagram = models.URLField("Instagram", blank=True)
    scholar_link = models.URLField("Google Scholar", blank=True)
    personal_website = models.URLField("Site web personnel", blank=True)

    # 5. Consentement
    consent = models.BooleanField("Consentement au traitement de la demande", default=False)

    # Suivi back-office
    status = models.CharField("Statut de la demande", max_length=10, choices=Status.choices,
                              default=Status.PENDING, db_index=True)
    created_at = models.DateTimeField("Reçue le", auto_now_add=True)
    reviewed_at = models.DateTimeField("Traitée le", null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reviewed_applications', verbose_name="Traitée par",
    )
    revoked_at = models.DateTimeField("Révoquée le", null=True, blank=True)
    revoked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='revoked_applications', verbose_name="Révoquée par",
    )
    revocation_reason = models.TextField("Motif de révocation", blank=True)
    internal_notes = models.TextField("Notes internes", blank=True)
    # Compte membre créé (ou retrouvé) à la validation
    member = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='membership_application', verbose_name="Compte membre",
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Demande d'adhésion"
        verbose_name_plural = "Demandes d'adhésion"

    def __str__(self):
        return f"{self.full_name} ({self.get_status_display()})"

    def _split_name(self):
        """« Nom et prénom(s) » : premier mot = nom, le reste = prénom(s)."""
        parts = self.full_name.split()
        return (parts[0], ' '.join(parts[1:])) if parts else ('', '')

    def how_heard_display(self):
        labels = dict(self.HowHeard.choices)
        items = [labels.get(c, c) for c in (self.how_heard_choices or [])]
        if self.how_heard:
            items.append(f"Précision : {self.how_heard}")
        return items

    def _activate_member(self):
        """Crée le compte membre (rôle « membre », sans mot de passe) ou réactive l'existant,
        et reporte le profil public renseigné dans la demande (sans écraser l'existant)."""
        UserModel = get_user_model()
        email = self.email.lower().strip()
        member = self.member or UserModel.objects.filter(email__iexact=email).first()
        if member is None:
            nom, prenom = self._split_name()
            member = UserModel(username=email, email=email, nom=nom, prenom=prenom, role='membre')
            member.set_unusable_password()

        def fill(field, value):
            if value and not getattr(member, field):
                setattr(member, field, value)

        fill('department', self.institution)
        fill('job_title', self.get_academic_status_display())
        fill('phone_number', self.phone)
        # La biographie est affichée avec |safe sur le site public : on échappe le texte saisi.
        fill('bio', linebreaks(escape(self.bio)) if self.bio else '')
        for field in ('social_linkedin', 'social_facebook', 'social_twitter', 'social_instagram',
                      'scholar_link', 'personal_website'):
            fill(field, getattr(self, field))
        if self.profile_picture and not member.profile_picture:
            self.profile_picture.open('rb')
            try:
                member.profile_picture.save(
                    os.path.basename(self.profile_picture.name), ContentFile(self.profile_picture.read()),
                    save=False)
            finally:
                self.profile_picture.close()

        member.is_active = True
        member.save()
        self.member = member

    def _deactivate_member(self):
        """Retire le membre de la liste publique ; un admin/modérateur n'est jamais désactivé."""
        if self.member and self.member.role == 'membre':
            self.member.is_active = False
            self.member.save()

    def approve(self, user):
        self.status = self.Status.APPROVED
        self.reviewed_at = timezone.now()
        self.reviewed_by = user
        self.revoked_at = None
        self.revoked_by = None
        self._activate_member()
        self.save()

    def reject(self, user):
        self.status = self.Status.REJECTED
        self.reviewed_at = timezone.now()
        self.reviewed_by = user
        self.save()

    def revoke(self, user, reason=''):
        """Seule une adhésion validée peut être révoquée."""
        if self.status != self.Status.APPROVED:
            raise ValueError("Seule une adhésion validée peut être révoquée.")
        self.status = self.Status.REVOKED
        self.revoked_at = timezone.now()
        self.revoked_by = user
        self.revocation_reason = reason
        self._deactivate_member()
        self.save()

    def reset_to_pending(self):
        self.status = self.Status.PENDING
        self.reviewed_at = self.reviewed_by = None
        self.revoked_at = self.revoked_by = None
        self.revocation_reason = ''
        self._deactivate_member()
        self.save()


class PublicationNotice(models.Model):
    """Trace l'annonce d'un contenu aux abonnés : un contenu n'est annoncé qu'une fois."""
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    sent_count = models.PositiveIntegerField(_('envoyés'), default=0)
    created_at = models.DateTimeField(_('annoncé le'), auto_now_add=True)

    class Meta:
        verbose_name = _('annonce de publication')
        verbose_name_plural = _('annonces de publication')
        unique_together = ('content_type', 'object_id')


class PublicationDelivery(models.Model):
    """Un envoi d'annonce à un abonné : créé à la publication, envoyé ensuite par lots (commande send_pending_emails)."""
    notice = models.ForeignKey(PublicationNotice, on_delete=models.CASCADE, related_name='deliveries')
    subscriber = models.ForeignKey(NewsletterSubscriber, on_delete=models.CASCADE, related_name='deliveries')
    sent_at = models.DateTimeField(_('envoyé le'), null=True, blank=True)
    attempts = models.PositiveSmallIntegerField(_('tentatives'), default=0)
    last_error = models.CharField(_('dernière erreur'), max_length=255, blank=True)

    class Meta:
        verbose_name = _("envoi d'annonce")
        verbose_name_plural = _("envois d'annonces")
        unique_together = ('notice', 'subscriber')


class BlockedSender(models.Model):
    """Adresse e-mail à qui l'envoi des formulaires publics (contact, adhésion, info-lettre) est refusé."""
    email = models.EmailField("Adresse e-mail", unique=True)
    blocked_at = models.DateTimeField("Bloquée le", auto_now_add=True)
    blocked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='blocked_senders', verbose_name="Bloquée par")

    class Meta:
        verbose_name = "Expéditeur bloqué"
        verbose_name_plural = "Expéditeurs bloqués"
        ordering = ['-blocked_at']

    def save(self, *args, **kwargs):
        self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email

    @classmethod
    def is_blocked(cls, email):
        email = (email or '').strip().lower()
        return bool(email) and cls.objects.filter(email=email).exists()
