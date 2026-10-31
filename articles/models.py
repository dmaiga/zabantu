# articles/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.text import slugify, Truncator
from tinymce.models import HTMLField
from django.utils import timezone
import uuid
import re
from intervenants.models import Intervenant
from django.urls import reverse
User = get_user_model()


def article_upload_path(instance, filename):
    return f'articles/{uuid.uuid4()}_{filename}'

# articles/models.py
class Article(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Brouillon'),
        ('scheduled', 'Programmé'),
        ('published', 'Publié'),
    )
    
    ARTICLE_TYPE_CHOICES = (
        ('zabantu', 'Zabantu'),
        ('academic', 'Académique'),
        ('independent', 'Indépendant'),
        ('analyse', 'Analyses'),
        ('article', 'Articles'),
        ('policy', 'Policy Briefs'),
        ('ouvrage', 'Ouvrages'),
        ('rapport', 'Rapports'),
        ('working', 'Working Paper'),
    )


    # Type d'article
    article_type = models.CharField(
        max_length=20,
        choices=ARTICLE_TYPE_CHOICES,
        default='zabantu',
        verbose_name="Type d'article"
    )

    # Champs communs à tous les types
    title = models.CharField(max_length=255, verbose_name="Titre")
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    status = models.CharField(
        max_length=10, 
        choices=STATUS_CHOICES, 
        default='draft', 
        verbose_name="Statut"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Date de modification")
    publish_at = models.DateTimeField(blank=True, null=True, verbose_name="Date de publication")
    # Champs spécifiques à Zabantu
    subtitle = models.CharField(max_length=500, blank=True, null=True, verbose_name="Sous-titre")
    authors = models.ManyToManyField(User, related_name='articles', verbose_name="Auteurs Zabantu")
    content = HTMLField(blank=True, null=True, verbose_name="Contenu")
    

    cover_image = models.ImageField(upload_to='articles/covers/', blank=True, null=True, verbose_name="Image de couverture")
    # Working paper fields
    institution = models.CharField(max_length=255, blank=True, null=True)
    working_number = models.CharField(max_length=50, blank=True, null=True)
    working_series = models.CharField(max_length=255, blank=True, null=True)
    
    working_year = models.IntegerField(blank=True, null=True)
    
    # Champs spécifiques aux articles académiques
    academic_authors = models.TextField(blank=True, null=True, verbose_name="Auteurs externes")
    publication_year = models.IntegerField(blank=True, null=True, verbose_name="Année de publication")
    journal = models.CharField(max_length=255, blank=True, null=True, verbose_name="Revue")
    publisher = models.CharField(max_length=255, blank=True, null=True, verbose_name="Éditeur")
    abstract = models.TextField(blank=True, null=True, verbose_name="Résumé")

    # Champs spécifiques aux articles indépendants
    external_author = models.CharField(max_length=255, blank=True, null=True, verbose_name="Auteur externe")
    external_link = models.URLField(blank=True, null=True, verbose_name="Lien vers l'article")
    external_link_academique = models.URLField(blank=True, null=True, verbose_name="Lien vers l'article Académique")
    independent_cover = models.ImageField(upload_to='articles/independent/', blank=True, null=True, 
                                        verbose_name="Image de couverture (facultatif)")

    resume = models.TextField(blank=True, null=True, verbose_name="Résumé") 
    # Fichiers
    pdf_file = models.FileField(upload_to=article_upload_path, blank=True, null=True, verbose_name="Fichier PDF")

    # Métadonnées SEO
    meta_title = models.CharField(max_length=60, blank=True, verbose_name="Titre SEO")
    meta_description = models.CharField(max_length=160, blank=True, verbose_name="Description SEO")

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Article"
        verbose_name_plural = "Articles"

    def __str__(self):
        return self.title

    def is_published(self):
        """Vérifie si l'article est publié"""
        return self.status == 'published'

    def get_public_url(self):
        return reverse('public_article_detail', args=[self.slug])

    def save(self, *args, **kwargs):
        # Génération automatique du slug
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while Article.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug

        # Métadonnées SEO
        if not self.meta_title:
            self.meta_title = Truncator(self.title).chars(60)

        # Date de publication automatique
        if self.status == 'published' and not self.publish_at:
            self.publish_at = timezone.now()
        elif self.status == 'scheduled' and not self.publish_at:
            self.status = 'draft'  # une programmation sans date n'a pas de sens
        elif self.status == 'draft':
            self.publish_at = None

        super().save(*args, **kwargs)

    def get_publication_status(self):
        """Retourne le statut de publication avec plus de détails"""
        if self.status == 'published':
            return f"Publié le {self.publish_at.strftime('%d/%m/%Y à %H:%M')}"
        else:
            return "Brouillon"
    
    def get_display_authors(self):
        """Retourne les auteurs formatés selon le type d'article"""
        if self.article_type == 'independent' and self.external_author:
            return [{'name': self.external_author, 'type': 'external', 'url': None}]
        elif self.article_type == 'academic' and self.academic_authors:
            authors = []
            if self.authors.exists():
                for author in self.authors.all():
                    authors.append({
                        'name': author.get_full_name(),
                        'type': 'zabantu',
                        'url': reverse('public_member_detail', args=[author.pk]),
                        'user': author
                    })
            # Ajouter les auteurs académiques externes
            if self.academic_authors:
                authors.append({
                    'name': self.academic_authors,
                    'type': 'academic',
                    'url': None
                })
            return authors
        else:
            # Articles Zabantu
            authors = []
            for author in self.authors.all():
                authors.append({
                    'name': author.get_full_name(),
                    'type': 'zabantu',
                    'url': reverse('public_member_detail', args=[author.pk]),
                    'user': author
                })
            return authors
    
    def has_external_link(self):
        """Vérifie si l'article a un lien externe"""
        return bool(self.external_link)
    
    def get_clean_external_link(self):
        """Retourne le lien externe formaté"""
        if self.external_link:
            # Enlever le protocole pour un affichage plus propre
            return self.external_link.replace('https://', '').replace('http://', '')
    def get_clean_external_link_academique(self):
        """Retourne le lien externe formaté"""
        if self.external_link:
            # Enlever le protocole pour un affichage plus propre
            return self.external_link.replace('https://', '').replace('http://', '')
        return None

#==================================================
#
#
#
#=================================================

def guelekan_upload_path(instance, filename):
    return f'guelekan/files/{uuid.uuid4()}_{filename}'
class Guelekan(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Brouillon'),
        ('scheduled', 'Programmé'),
        ('published', 'Publié'),
    )

    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, editable=False)  # editable=False pour le cacher
    subtitle = models.CharField(max_length=500, blank=True)
    content = HTMLField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')

    cover_image = models.ImageField(upload_to='guelekan/covers/', blank=True, null=True)
    pdf_file = models.FileField(upload_to='guelekan/pdfs/%Y/%m/%d/', blank=True, null=True)

    # Relation vers les galeries
    galleries = models.ManyToManyField(
        'gallery.Gallery',
        blank=True,
        verbose_name="Galeries associées",
        help_text="Sélectionnez les galeries de photos à associer à ce séminaire"
    )

    # Champ pour les invités (speakers/participants)
    intervenants = models.ManyToManyField(
        Intervenant,
        blank=True,
        related_name="guelekan_seminars",
        verbose_name="Intervenants"
    )

    meta_title = models.CharField(max_length=60, blank=True, editable=False)  # editable=False
    meta_description = models.CharField(max_length=160, blank=True, editable=False)  # editable=False

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    publish_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date de publication programmée"
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Séminaire Guelekan"
        verbose_name_plural = "Séminaires Guelekan"

    def __str__(self):
        return self.title

  
    def get_intervenants_list(self):
        """Retourne la liste des intervenants sous forme de noms complets"""
        return [i.full_name() for i in self.intervenants.all()]
    
    def get_guests_list(self):
        """Retourne la liste des invités sous forme de liste"""
        if self.guests:
            return [guest.strip() for guest in self.guests.split('\n') if guest.strip()]
        return []

    def save(self, *args, **kwargs):
        # Générer le slug automatiquement
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while Guelekan.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        
        # Générer les métadonnées automatiquement
        if not self.meta_title:
            self.meta_title = Truncator(self.title).chars(60)
        if not self.meta_description:
            # Nettoyer le HTML du contenu
            clean_content = re.sub('<[^<]+?>', '', self.content)
            # Utiliser le sous-titre si disponible, sinon le contenu
            description_source = self.subtitle if self.subtitle else clean_content
            self.meta_description = Truncator(description_source).chars(160)

        if self.status == 'scheduled' and not self.publish_at:
            self.status = 'draft'  # une programmation sans date n'a pas de sens

        super().save(*args, **kwargs)
    
    def get_public_url(self):
        return reverse('public_guelekan_detail', args=[self.slug])

    def is_visible(self):
        """Vérifie si l'article est publié ET que la date de publication est passée"""
        return (self.status == 'published' and 
                (self.publish_at is None or self.publish_at <= timezone.now()))
    
    def is_published(self):
        """Alias pour la compatibilité"""
        return self.is_visible()
    
    def get_intervenants_list(self):
        """Retourne la liste des intervenants sous forme de noms complets"""
        return [i.full_name() for i in self.intervenants.all()]