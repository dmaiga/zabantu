from django.db.models.signals import post_save
from django.dispatch import receiver

from articles.models import Article, Guelekan
from events.models import Event

from .mailing import queue_publication


@receiver(post_save, sender=Article)
@receiver(post_save, sender=Guelekan)
@receiver(post_save, sender=Event)
def queue_announcement(sender, instance, raw=False, **kwargs):
    """Un contenu publié est mis en file pour annonce aux abonnés ; l'envoi se fait hors requête, par cron."""
    if not raw and instance.status == 'published':
        queue_publication(instance)
