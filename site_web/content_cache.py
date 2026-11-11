"""Cache des morceaux de pages publiques, invalidé à chaque changement de contenu.

Les gabarits mettent en cache avec {% cache PAGE_CACHE_TIMEOUT nom content_version ... %}.
Un numéro de version unique (dans le cache par défaut, en fichiers, donc partagé entre les
processus de l'hébergeur et le cron) change dès qu'un contenu public est créé, modifié ou
supprimé : toutes les clés précédentes deviennent inutilisées d'un coup, sans les chercher.
La durée de vie courte (PAGE_CACHE_TIMEOUT) couvre ce qui change avec le temps seul
(un événement « à venir » qui passe) et ce qui contourne les signaux (QuerySet.update).
"""
import time

from django.core.cache import cache
from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import receiver

VERSION_KEY = 'content_version'

# Modèles dont le contenu s'affiche sur les pages publiques (« app.Modèle »).
WATCHED = {
    'articles.Article', 'articles.Guelekan', 'events.Event', 'gallery.Gallery', 'gallery.Photo',
    'intervenants.Intervenant', 'users.CustomUser', 'users.Partenaire',
}


def content_version():
    version = cache.get(VERSION_KEY)
    if version is None:
        version = bump()
    return version


def bump():
    version = str(time.time_ns())
    cache.set(VERSION_KEY, version, None)
    return version


def _watched(model):
    return model._meta.label in WATCHED


@receiver(post_save)
def _on_save(sender, raw=False, update_fields=None, **kwargs):
    if raw or not _watched(sender):
        return
    if update_fields and set(update_fields) <= {'last_login'}:  # simple connexion d'un membre
        return
    if getattr(kwargs.get('instance'), 'role', None) == 'participant':  # compte des formations : jamais affiché
        return
    bump()


@receiver(post_delete)
def _on_delete(sender, **kwargs):
    if _watched(sender):
        bump()


@receiver(m2m_changed)
def _on_m2m(sender, instance, action, **kwargs):
    if action.startswith('post_') and _watched(type(instance)):
        bump()
