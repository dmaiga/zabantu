from django.core.mail import EmailMultiAlternatives
from django.conf import settings
import smtplib

def get_newsletter_connection():
    """Crée une connexion SMTP pour la newsletter"""
    from django.core.mail import get_connection
    
    connection = get_connection(
        backend='django.core.mail.backends.smtp.EmailBackend',
        host=settings.EMAIL_HOST_NEWS,
        port=settings.EMAIL_PORT_NEWS,
        username=settings.EMAIL_HOST_USER_NEWS,
        password=settings.EMAIL_HOST_PASSWORD_NEWS,
        use_ssl=settings.EMAIL_USE_SSL_NEWS
    )
    return connection

def send_newsletter_email(subject, html_content, to_emails):
    """Envoie un email de newsletter"""
    from django.utils.html import strip_tags
    
    text_content = strip_tags(html_content)
    
    try:
        # Créer l'email avec la connexion newsletter
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL_NEWS,
            to=to_emails,
            connection=get_newsletter_connection()
        )
        email.attach_alternative(html_content, "text/html")
        
        # Envoyer l'email
        email.send()
        return True
    except Exception as e:
        print(f"Erreur lors de l'envoi de l'email: {e}")
        return False