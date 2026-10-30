from django.db import models
from django.conf import settings

class Intervenant(models.Model):
    TYPE_INTERVENANT_CHOICES = [
        ('moderator', 'Modérateur'),
        ('speaker', 'Intervenant'),
        ('trainer', 'Formateur'),
        ('panelist', 'Panéliste'),
        ('expert', 'Expert'),
    ]
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='intervenant_profile'
    )
    
    first_name = models.CharField(max_length=100, verbose_name="Prénom")
    last_name = models.CharField(max_length=100, verbose_name="Nom")
    email = models.EmailField(unique=True, verbose_name="Email")
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Téléphone")
    organization = models.CharField(max_length=200, verbose_name="Organisation")
    position = models.CharField(max_length=200, blank=True, null=True, verbose_name="Poste")
    
    bio = models.TextField(verbose_name="Biographie")
    expertise = models.CharField(max_length=300, blank=True, null=True, verbose_name="Domaines d'expertise")
    
    intervenant_type = models.CharField(
        max_length=20,
        choices=TYPE_INTERVENANT_CHOICES,
        verbose_name="Type d'intervenant"
    )
    
    photo = models.ImageField(
        upload_to='intervenants/', 
        blank=True, 
        null=True,
        verbose_name="Photo de profil"
    )
    
    # Liens sociaux
    linkedin = models.URLField(blank=True, null=True, verbose_name="LinkedIn")
    facebook = models.URLField(blank=True, null=True, verbose_name="facebook")
    website = models.URLField(blank=True, null=True, verbose_name="Site web")
    
    # Métadonnées
    is_available = models.BooleanField(default=True, verbose_name="Disponible pour de nouveaux événements")
    note_internal = models.TextField(blank=True, null=True, verbose_name="Notes internes")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Intervenant"
        verbose_name_plural = "Intervenants"
        ordering = ['last_name', 'first_name']
        indexes = [
            models.Index(fields=['last_name', 'first_name']),
            models.Index(fields=['intervenant_type']),
            models.Index(fields=['organization']),
        ]
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.organization}"
    
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def type_display(self):
        return dict(self.TYPE_INTERVENANT_CHOICES).get(self.intervenant_type, self.intervenant_type)