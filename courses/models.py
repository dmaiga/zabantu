"""Formations : comptes participants, cours, cohortes et inscriptions.

Un participant (rôle « participant » de CustomUser) peut être étudiant(e), chercheur(e), professionnel(le)… : son profil
est dans ParticipantProfile. Les fichiers de cours sont rangés hors de MEDIA_ROOT (dossier privé) et servis par une vue
qui vérifie l'accès.
"""
import os
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from site_web.models import MembershipApplication
from zabantu.i18n import TranslatableMixin

COURSE_FILE_EXTENSIONS = ('pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx', 'odt', 'odp', 'ods', 'zip', 'txt', 'csv')
MAX_COURSE_FILE_MB = 50


class PrivateStorage(FileSystemStorage):
    """Stockage des fichiers de cours : PRIVATE_MEDIA_ROOT (lu à chaque usage), jamais servi par le serveur web."""

    @property
    def base_location(self):
        return settings.PRIVATE_MEDIA_ROOT

    @property
    def location(self):
        return os.path.abspath(self.base_location)

    def url(self, name):
        raise ValueError("Fichier privé : utiliser la vue participant_course_file.")


def private_storage():
    """Stockage passé en fonction : la migration ne garde aucun chemin propre à une machine."""
    return PrivateStorage()


def validate_course_file(upload):
    if getattr(upload, '_committed', False):
        return
    extension = os.path.splitext(upload.name or '')[1].lower().lstrip('.')
    if extension not in COURSE_FILE_EXTENSIONS:
        raise ValidationError("Format non accepté. Formats possibles : " + ', '.join(COURSE_FILE_EXTENSIONS).upper() + '.')
    if upload.size > MAX_COURSE_FILE_MB * 1024 * 1024:
        raise ValidationError(f"Le fichier ne doit pas dépasser {MAX_COURSE_FILE_MB} Mo.")


def course_file_path(instance, filename):
    return f'courses/{instance.course_id}/{uuid.uuid4().hex[:8]}_{filename}'


class ParticipantProfile(models.Model):
    """Profil d'un compte participant : qui il est (le public varie) et ses préférences."""
    Status = MembershipApplication.AcademicStatus   # mêmes choix que la demande d'adhésion

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='participant_profile')
    status = models.CharField(_("Profil"), max_length=30, choices=Status.choices)
    organization = models.CharField(_("Organisation (université, entreprise, institution…)"), max_length=255, blank=True)
    language = models.CharField("Langue", max_length=5, choices=settings.LANGUAGES, default='fr')
    notify_cohorts = models.BooleanField(_("Me prévenir par e-mail de l'ouverture des formations"), default=True)
    created_at = models.DateTimeField("Créé le", auto_now_add=True)

    class Meta:
        verbose_name = "profil de participant"
        verbose_name_plural = "profils de participants"

    def __str__(self):
        return str(self.user)


class Course(TranslatableMixin, models.Model):
    TRANSLATED_FIELDS = ('title', 'summary')
    MAIN_FIELDS = ('title', 'summary')

    title = models.CharField("Titre", max_length=255)
    summary = models.TextField("Résumé", blank=True)
    title_en = models.CharField("Titre (anglais)", max_length=255, blank=True)
    summary_en = models.TextField("Résumé (anglais)", blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='created_courses', verbose_name="Créé par")
    created_at = models.DateTimeField("Créé le", auto_now_add=True)
    updated_at = models.DateTimeField("Modifié le", auto_now=True)

    class Meta:
        ordering = ['title']
        verbose_name = "cours"
        verbose_name_plural = "cours"

    def __str__(self):
        return self.title

    def is_accessible_by(self, user):
        """L'équipe voit tous les cours ; un participant, ceux des cohortes où il est accepté."""
        if not user.is_authenticated:
            return False
        if getattr(user, 'can_moderate', False):
            return True
        return Enrollment.objects.filter(user=user, status=Enrollment.Status.ACCEPTED, cohort__courses=self).exists()


class CourseFile(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='files', verbose_name="Cours")
    title = models.CharField("Titre", max_length=255, blank=True)
    file = models.FileField("Fichier", upload_to=course_file_path, storage=private_storage,
                            validators=[validate_course_file])
    order = models.PositiveIntegerField("Ordre", default=0)
    uploaded_at = models.DateTimeField("Ajouté le", auto_now_add=True)

    class Meta:
        ordering = ['order', 'uploaded_at']
        verbose_name = "fichier de cours"
        verbose_name_plural = "fichiers de cours"

    def __str__(self):
        return self.display_name

    @property
    def filename(self):
        return os.path.basename(self.file.name).split('_', 1)[-1]

    @property
    def display_name(self):
        return self.title or self.filename

    @property
    def extension(self):
        return os.path.splitext(self.file.name)[1].lower().lstrip('.')


class CohortQuerySet(models.QuerySet):
    def open(self, day=None):
        """Cohortes actives dont les inscriptions sont ouvertes aujourd'hui (dates incluses)."""
        day = day or timezone.localdate()
        return self.filter(is_active=True, opens_on__lte=day, closes_on__gte=day)


class Cohort(TranslatableMixin, models.Model):
    TRANSLATED_FIELDS = ('name', 'description')
    MAIN_FIELDS = ('name', 'description')

    name = models.CharField("Nom", max_length=255)
    description = models.TextField("Présentation", blank=True)
    name_en = models.CharField("Nom (anglais)", max_length=255, blank=True)
    description_en = models.TextField("Présentation (anglais)", blank=True)
    opens_on = models.DateField("Ouverture des inscriptions")
    closes_on = models.DateField("Fermeture des inscriptions")
    courses = models.ManyToManyField(Course, blank=True, related_name='cohorts', verbose_name="Cours")
    announced_at = models.DateTimeField("Annoncée le", null=True, blank=True, editable=False)
    # Désactivée : la cohorte disparaît du site et n'accepte plus d'inscription ; les participants déjà acceptés
    # gardent l'accès à leurs cours (ils les ont suivis), sauf révocation.
    is_active = models.BooleanField("Active", default=True)
    # Message de la campagne d'annonce (rédigé au backoffice), repris dans l'e-mail envoyé aux participants
    announcement_subject = models.CharField("Objet de l'annonce", max_length=200, blank=True)
    announcement_message = models.TextField("Message de l'annonce", blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='created_cohorts', verbose_name="Créée par")
    created_at = models.DateTimeField("Créée le", auto_now_add=True)

    objects = CohortQuerySet.as_manager()

    class Meta:
        ordering = ['-opens_on']
        verbose_name = "cohorte"
        verbose_name_plural = "cohortes"

    def __str__(self):
        return self.name

    def clean(self):
        if self.opens_on and self.closes_on and self.closes_on < self.opens_on:
            raise ValidationError({'closes_on': "La fermeture doit suivre l'ouverture des inscriptions."})

    @property
    def is_open(self):
        return self.is_active and self.opens_on <= timezone.localdate() <= self.closes_on

    @property
    def state(self):
        if not self.is_active:
            return 'disabled'
        today = timezone.localdate()
        if today < self.opens_on:
            return 'upcoming'
        return 'open' if today <= self.closes_on else 'closed'


class Enrollment(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', _('En attente')
        ACCEPTED = 'accepted', _('Acceptée')
        REJECTED = 'rejected', _('Refusée')
        REVOKED = 'revoked', _('Révoquée')

    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE, related_name='enrollments', verbose_name="Cohorte")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='enrollments',
                             verbose_name="Participant")
    motivation = models.TextField(_("Pourquoi souhaitez-vous suivre cette formation ?"))
    expectations = models.TextField(_("Qu'en attendez-vous ? (facultatif)"), blank=True)
    status = models.CharField("Statut", max_length=10, choices=Status.choices, default=Status.PENDING, db_index=True)
    created_at = models.DateTimeField("Reçue le", auto_now_add=True)
    decided_at = models.DateTimeField("Décision le", null=True, blank=True)
    decided_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='decided_enrollments', verbose_name="Décision par")

    class Meta:
        ordering = ['-created_at']
        constraints = [models.UniqueConstraint(fields=['cohort', 'user'], name='unique_enrollment_per_cohort')]
        verbose_name = "inscription"
        verbose_name_plural = "inscriptions"

    def __str__(self):
        return f"{self.user} → {self.cohort}"

    # Transitions permises : action → statuts de départ
    TRANSITIONS = {
        'accept': (Status.PENDING, Status.REJECTED, Status.REVOKED),
        'reject': (Status.PENDING,),
        'revoke': (Status.ACCEPTED,),
    }
    TARGET = {'accept': Status.ACCEPTED, 'reject': Status.REJECTED, 'revoke': Status.REVOKED}

    def can(self, action):
        return self.status in self.TRANSITIONS.get(action, ())

    def decide(self, action, by):
        """Applique la décision si elle est permise ; renvoie True si le statut a changé."""
        if not self.can(action):
            return False
        self.status = self.TARGET[action]
        self.decided_at = timezone.now()
        self.decided_by = by
        self.save(update_fields=['status', 'decided_at', 'decided_by'])
        return True


class CohortAnnouncement(models.Model):
    """Annonce de l'ouverture d'une cohorte à un participant (file d'envoi, retentée en cas d'échec)."""
    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE, related_name='announcements')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cohort_announcements')
    sent_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.CharField(max_length=255, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['cohort', 'user'], name='unique_cohort_announcement')]
        indexes = [models.Index(fields=['cohort'], condition=models.Q(sent_at=None), name='announcement_pending_idx')]


class CourseFileDownload(models.Model):
    """Téléchargement d'un fichier de cours par un participant : sert à mesurer l'intérêt et l'assiduité
    (fiche du participant au backoffice). Les téléchargements de l'équipe ne sont pas comptés."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='course_downloads')
    course_file = models.ForeignKey(CourseFile, on_delete=models.CASCADE, related_name='downloads')
    downloaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-downloaded_at']
        indexes = [models.Index(fields=['user', 'course_file'], name='download_user_file_idx')]
