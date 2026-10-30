# gallery/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.text import slugify
import uuid

User = get_user_model()

class Gallery(models.Model):
    title = models.CharField(max_length=200, verbose_name="Titre")
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    description = models.TextField(blank=True, verbose_name="Description")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_featured = models.BooleanField(
        default=False, 
        verbose_name="À la une",
        help_text="Mettre en avant cette galerie sur la page d'accueil"
    )
    cover_image = models.ImageField(
        upload_to='galleries/covers/', 
        blank=True, 
        null=True,
        verbose_name="Image de couverture",
        help_text="Image représentative de la galerie"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Créé par",
        related_name='created_galleries'
    )

    class Meta:
        verbose_name = "Galerie"
        verbose_name_plural = "Galeries"
        ordering = ['-created_at']
        permissions = [
            ("can_manage_all_galleries", "Peut gérer toutes les galeries"),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # Génération automatique du slug si vide
        if not self.slug:
            base_slug = slugify(self.title)
            unique_slug = base_slug
            num = 1
            while Gallery.objects.filter(slug=unique_slug).exists():
                unique_slug = f"{base_slug}-{uuid.uuid4().hex[:4]}"
                num += 1
            self.slug = unique_slug
        
        # Si nouvelle galerie et created_by non défini
        if not self.pk and not self.created_by and hasattr(self, 'request_user'):
            self.created_by = self.request_user
        
        super().save(*args, **kwargs)

    @property
    def photo_count(self):
        """Retourne le nombre de photos dans la galerie"""
        return self.photos.count()

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('gallery_detail', kwargs={'slug': self.slug})

class Photo(models.Model):
    gallery = models.ForeignKey(
        Gallery, 
        on_delete=models.CASCADE, 
        related_name='photos',
        blank=True,
        null=True,
        verbose_name="Galerie associée"
    )
    title = models.CharField(
        max_length=200, 
        verbose_name="Titre",
        help_text="Titre descriptif de la photo"
    )
    image = models.ImageField(
        upload_to='galleries/photos/%Y/%m/%d/',
        verbose_name="Fichier image"
    )
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Uploadé par",
        related_name='uploaded_photos'
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_standalone = models.BooleanField(
        default=False,
        verbose_name="Photo indépendante",
        help_text="Cocher si cette photo n'appartient à aucune galerie"
    )
    tags = models.ManyToManyField(
        'PhotoTag',
        blank=True,
        verbose_name="Mots-clés"
    )

    class Meta:
        verbose_name = "Photo"
        verbose_name_plural = "Photos"
        ordering = ['-uploaded_at']
        permissions = [
            ("can_manage_all_photos", "Peut gérer toutes les photos"),
        ]

    def __str__(self):
        return self.title or f"Photo #{self.id}"

    def save(self, *args, **kwargs):
        # Si nouvelle photo et uploaded_by non défini
        if not self.pk and not self.uploaded_by and hasattr(self, 'request_user'):
            self.uploaded_by = self.request_user
        
        # Vérification cohérence galerie/standalone
        if not self.gallery and not self.is_standalone:
            self.is_standalone = True
            
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('photo_detail', kwargs={'pk': self.pk})


class PhotoTag(models.Model):
    """Modèle pour les tags/catégories de photos"""
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Tag photo"
        verbose_name_plural = "Tags photos"
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)