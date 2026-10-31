"""Réglages des tests : base SQLite en mémoire, rapide, qui ne touche jamais aux données.

Le rôle PostgreSQL de l'hébergeur n'a pas le droit de créer une base, or Django en crée une pour les tests.
`python manage.py test` utilise donc ce fichier automatiquement (voir manage.py).
Pour tester sur PostgreSQL, indiquer `DJANGO_SETTINGS_MODULE=zabantu.settings` avec un rôle qui peut créer des bases."""
import os

# Valeurs factices : seul le chargement des réglages les exige, aucune connexion PostgreSQL n'est ouverte.
for _name in ('DB_NAME', 'DB_USER', 'DB_PASSWORD'):
    os.environ.setdefault(_name, 'test')
os.environ.setdefault('EMAIL_BACKEND', 'django.core.mail.backends.locmem.EmailBackend')
os.environ.setdefault('DEBUG', 'True')
os.environ.setdefault('SITE_URL', 'http://testserver')

from .settings import *  # noqa: E402,F401,F403

DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']  # tests plus rapides
CACHES = {name: {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache', 'LOCATION': name} for name in ('default', 'antispam')}
