# site_web/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache

# Importez les modèles depuis leurs applications respectives
from articles.models import Article, Guelekan
from events.models import Event
from gallery.models import Gallery, Photo
from users.models import CustomUser

@receiver([post_save, post_delete], sender=Article)
def clear_article_cache(sender, **kwargs):
    cache.delete_many(['home_page', 'about_page', 'membre_liste'])
    # Supprimer tous les caches liés aux articles
    for key in cache._cache:
        if key.startswith('article_list_'):
            cache.delete(key)

@receiver([post_save, post_delete], sender=Event)
def clear_event_cache(sender, **kwargs):
    cache.delete('home_page')

@receiver([post_save, post_delete], sender=Gallery)
def clear_gallery_cache(sender, **kwargs):
    cache.delete('liste_galeries')
    # Supprimer les caches de détail des galeries
    for key in cache._cache:
        if key.startswith('galerie_detail_'):
            cache.delete(key)

@receiver([post_save, post_delete], sender=Photo)
def clear_photo_cache(sender, **kwargs):
    cache.delete('toutes_photos')
    # Supprimer les caches de détail des photos
    for key in cache._cache:
        if key.startswith('photo_detail_'):
            cache.delete(key)

@receiver([post_save, post_delete], sender=CustomUser)
def clear_user_cache(sender, **kwargs):
    cache.delete_many(['about_page', 'membre_liste'])

@receiver([post_save, post_delete], sender=Guelekan)
def clear_guelekan_cache(sender, **kwargs):
    cache.delete('home_page')