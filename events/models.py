from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class Event(models.Model):
    EVENT_TYPE_CHOICES = [
        ('conference', 'Conférence'),
        ('formation', 'Formation'),
        ('seminaire', 'Séminaire Gɛlɛkan'),
        ('webinaire', 'Webinaire'),
        ('atelier', 'Atelier'),
        ('autre', 'Autre'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Brouillon'),
        ('published', 'Publié'),
        ('archived', 'Archivé'),
    ]
    
    # Champs existants...
    title = models.CharField(max_length=200, verbose_name="Titre")
    slug = models.SlugField(max_length=200, unique=True, blank=True, verbose_name="Slug")
    content = models.TextField(verbose_name="Contenu")
    image = models.ImageField(upload_to='events/', verbose_name="Image")
    
    # Nouveau champ de statut
    status = models.CharField(
        max_length=10, 
        choices=STATUS_CHOICES, 
        default='draft',
        verbose_name="Statut"
    )
    
    event_type = models.CharField(
        max_length=20,
        choices=EVENT_TYPE_CHOICES,
        default='seminaire',
        verbose_name="Type d'événement"
    )
    
    date = models.DateTimeField(verbose_name="Date et heure de début")
    end_date = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name="Date et heure de fin"
    )
    
    location = models.CharField(max_length=100, blank=True, null=True, verbose_name="Lieu")
    lieu_gps = models.URLField(max_length=550, blank=True, null=True, verbose_name="Lien GPS")
    
    is_webinar = models.BooleanField(default=False, verbose_name="Événement en ligne")
    webinar_link = models.URLField(max_length=500, blank=True, null=True, verbose_name="Lien de webinaire")
    
    is_featured = models.BooleanField(default=False, verbose_name="À la une")
    
    # Relations
    author = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='authored_events',
        verbose_name="Auteur"
    )
    
    intervenants = models.ManyToManyField(
        'intervenants.Intervenant',
        through='EventIntervenant',
        blank=True,
        verbose_name="Intervenants"
    )
    
    # Métadonnées analytiques
    target_audience = models.CharField(max_length=200, blank=True, null=True, verbose_name="Public cible")
    expected_attendees = models.PositiveIntegerField(blank=True, null=True, verbose_name="Nombre attendu de participants")
    primary_topic = models.CharField(max_length=100, blank=True, null=True, verbose_name="Thème principal")
    secondary_topics = models.CharField(max_length=300, blank=True, null=True, verbose_name="Thèmes secondaires")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True, verbose_name="Date de publication")
    
    class Meta:
        verbose_name = "Événement"
        verbose_name_plural = "Événements"
        ordering = ['-date']
        indexes = [
            models.Index(fields=['-date']),
            models.Index(fields=['status']),
            models.Index(fields=['event_type']),
        ]
        permissions = [
            ("publish_event", "Peut publier des événements"),
        ]
    
    @property
    def is_published(self):
        return self.status == 'published'
    
    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"
    
    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.title)
        
        # Mettre à jour la date de publication si le statut change à "published"
        if self.status == 'published' and not self.published_at:
            self.published_at = timezone.now()
        
        super().save(*args, **kwargs)
    
    def is_upcoming(self):
        return self.is_published and self.date >= timezone.now()
    
    def get_event_duration(self):
        if self.end_date:
            return f"{self.date.strftime('%d/%m/%Y %H:%M')} - {self.end_date.strftime('%d/%m/%Y %H:%M')}"
        return self.date.strftime('%d/%m/%Y %H:%M')
    
    def get_intervenants_by_type(self, intervenant_type):
        return self.intervenants.filter(eventintervenant__role=intervenant_type)


class EventIntervenant(models.Model):
    ROLE_CHOICES = [
        ('moderator', 'Modérateur'),
        ('speaker', 'Intervenant'),
        ('trainer', 'Formateur'),
        ('panelist', 'Panéliste'),
        ('expert', 'Expert'),
        ('host', 'Animateur'),
    ]
    
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    intervenant = models.ForeignKey('intervenants.Intervenant', on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, verbose_name="Rôle dans l'événement")
    order = models.PositiveIntegerField(default=0, verbose_name="Ordre d'affichage")
    note = models.TextField(blank=True, null=True, verbose_name="Notes spécifiques")
    
    class Meta:
        verbose_name = "Intervenant d'événement"
        verbose_name_plural = "Intervenants d'événement"
        ordering = ['order', 'intervenant__last_name']
        unique_together = ['event', 'intervenant']
    
    def __str__(self):
        return f"{self.intervenant} - {self.event}"