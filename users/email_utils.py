# users/email_utils.py
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def send_newsletter_email(subject, html_content, recipient_list):
    """
    Envoie un email de newsletter avec configuration spécifique
    """
    try:
        # Configuration spécifique pour la newsletter
        email_host = getattr(settings, 'EMAIL_HOST_NEWS', settings.EMAIL_HOST)
        email_port = getattr(settings, 'EMAIL_PORT_NEWS', settings.EMAIL_PORT)
        email_username = getattr(settings, 'EMAIL_HOST_USER_NEWS', settings.EMAIL_HOST_USER)
        email_password = getattr(settings, 'EMAIL_HOST_PASSWORD_NEWS', settings.EMAIL_HOST_PASSWORD)
        email_from = getattr(settings, 'DEFAULT_FROM_EMAIL_NEWS', settings.DEFAULT_FROM_EMAIL)
        
        # Créer le contenu texte à partir du HTML
        text_content = strip_tags(html_content)
        
        # Créer l'email
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=email_from,
            to=recipient_list,
            connection=None  # Utiliser la connexion par défaut
        )
        
        # Ajouter la version HTML
        email.attach_alternative(html_content, "text/html")
        
        # Envoyer l'email
        result = email.send()
        
        if result == 1:
            logger.info(f"Email envoyé avec succès à {recipient_list}")
            return True
        else:
            logger.error(f"Échec d'envoi d'email à {recipient_list}")
            return False
            
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi de la newsletter: {str(e)}")
        return False