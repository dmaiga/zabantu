# users/backends.py
from django.contrib.auth.backends import ModelBackend
from django.core.mail.backends.smtp import EmailBackend
from django.conf import settings
import os

class SupportEmailBackend(EmailBackend):
    """
    Backend personnalisé pour utiliser les credentials du support
    """
    def __init__(self, *args, **kwargs):
        # Utiliser les variables d'environnement ou les valeurs par défaut
        host = getattr(settings, 'EMAIL_HOST_SUPPORT', os.getenv('EMAIL_HOST_SUPPORT', 'mail.zabantu.net'))
        port = getattr(settings, 'EMAIL_PORT_SUPPORT', os.getenv('EMAIL_PORT_SUPPORT', 587))
        username = os.getenv('EMAIL_HOST_USER_SUPPORT')
        password = os.getenv('EMAIL_HOST_PASSWORD_SUPPORT')
        use_tls = getattr(settings, 'EMAIL_USE_TLS_SUPPORT', os.getenv('EMAIL_USE_TLS_SUPPORT', True))
        
        kwargs.update({
            'host': host,
            'port': port,
            'username': username,
            'password': password,
            'use_tls': use_tls,
            'fail_silently': False,
        })
        super().__init__(*args, **kwargs)


class BackofficeBackend(ModelBackend):
    """Authentification standard, réservée aux comptes qui ont accès au backoffice.

    `get_user` passe aussi par ici : retirer l'accès coupe les sessions déjà ouvertes."""

    def user_can_authenticate(self, user):
        return super().user_can_authenticate(user) and user.can_access_backoffice
