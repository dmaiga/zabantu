"""Envoi des e-mails du site : un seul point d'entrée pour la connexion, le rendu et le journal.

- notify_publication(obj)  : annonce une publication ou un événement aux abonnés actifs
- send_campaign(campaign)  : envoie une campagne d'infolettre à ses destinataires
- send_reply(...)          : réponse à un message de contact
"""
import html
import logging

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.mail import EmailMultiAlternatives, get_connection
from django.contrib.auth.tokens import default_token_generator
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.html import strip_tags
from django.utils.http import urlsafe_base64_encode
from django.utils.text import Truncator

from .models import NewsletterSubscriber, PublicationNotice

logger = logging.getLogger(__name__)

EXCERPT_FIELDS = ('resume', 'abstract', 'subtitle', 'content')


def absolute_url(path):
    return f"{settings.SITE_URL.rstrip('/')}{path}"


def unsubscribe_url(subscriber):
    return absolute_url(reverse('newsletter_unsubscribe', args=[subscriber.token]))


def newsletter_connection():
    """Connexion SMTP dédiée à l'infolettre (le backend suit EMAIL_BACKEND : console en dev, mémoire en test)."""
    return get_connection(
        host=settings.EMAIL_HOST_NEWS,
        port=settings.EMAIL_PORT_NEWS,
        username=settings.EMAIL_HOST_USER_NEWS,
        password=settings.EMAIL_HOST_PASSWORD_NEWS,
        use_tls=settings.EMAIL_USE_TLS_NEWS,
        use_ssl=settings.EMAIL_USE_SSL_NEWS,
    )


def _build_message(subscriber, subject, template, context, text):
    context = {**context, 'unsubscribe_url': unsubscribe_url(subscriber)}
    message = EmailMultiAlternatives(
        subject=subject,
        body=f"{text}\n\nSe désabonner : {context['unsubscribe_url']}",
        from_email=settings.DEFAULT_FROM_EMAIL_NEWS,
        to=[subscriber.email],
        headers={'List-Unsubscribe': f"<{context['unsubscribe_url']}>"},
    )
    message.attach_alternative(render_to_string(template, context), 'text/html')
    return message


def _deliver(messages):
    """Envoie {clé: message} sur une seule connexion ; renvoie (clés envoyées, clés en échec)."""
    sent, failed = [], []
    connection = newsletter_connection()
    try:
        connection.open()
    except Exception:
        logger.exception("Connexion au serveur d'infolettre impossible")
        return sent, list(messages)
    try:
        for key, message in messages.items():
            message.connection = connection
            try:
                delivered = message.send()
            except Exception:
                logger.exception("Échec d'envoi à %s", message.to)
                delivered = 0
            (sent if delivered else failed).append(key)
    finally:
        connection.close()
    return sent, failed


def _excerpt(obj):
    for field in EXCERPT_FIELDS:
        text = html.unescape(strip_tags(getattr(obj, field, None) or '')).strip()
        if text:
            return Truncator(text).words(50)
    return ''


def _is_event(obj):
    return obj.__class__.__name__ == 'Event'


def notify_publication(obj):
    """Annonce `obj` aux abonnés actifs, une seule fois. Renvoie (envoyés, échecs) ou None si rien n'est envoyé."""
    if not settings.SEND_NEWSLETTER_ON_PUBLISH:
        return None
    if _is_event(obj) and obj.date < timezone.now():
        return None  # inutile d'annoncer un événement déjà passé

    notice, created = PublicationNotice.objects.get_or_create(
        content_type=ContentType.objects.get_for_model(obj), object_id=obj.pk)
    if not created:
        return None

    label = 'Nouvel événement' if _is_event(obj) else 'Nouvelle publication'
    context = {
        'label': label,
        'title': obj.title,
        'excerpt': _excerpt(obj),
        'url': absolute_url(obj.get_public_url()),
        'closing': 'Nous espérons vous y retrouver.' if _is_event(obj)
                   else 'Nous espérons que cette publication vous plaira.',
    }
    text = f"{label} : {obj.title}\n\n{context['excerpt']}\n\nLire la suite : {context['url']}\n\n{context['closing']}"
    subscribers = {s.pk: s for s in NewsletterSubscriber.objects.filter(is_active=True)}
    messages = {pk: _build_message(s, f"{label} : {obj.title}", 'emails/publication.html', context, text)
                for pk, s in subscribers.items()}

    sent, failed = _deliver(messages)
    if failed and not sent:
        notice.delete()  # rien n'est parti : on pourra réessayer
    else:
        notice.sent_count = len(sent)
        notice.save(update_fields=['sent_count'])
    return len(sent), len(failed)


def send_campaign(campaign):
    """Envoie la campagne aux destinataires actifs et met à jour son statut. Renvoie (envoyés, échecs)."""
    campaign.status = 'sending'
    campaign.save(update_fields=['status'])

    recipients = {r.pk: r for r in campaign.recipients.select_related('subscriber')
                  .filter(subscriber__is_active=True)}
    context = {'title': campaign.title, 'body': campaign.content}
    text = strip_tags(campaign.content)
    messages = {pk: _build_message(r.subscriber, campaign.subject, 'emails/campaign.html', context, text)
                for pk, r in recipients.items()}

    sent, failed = _deliver(messages)
    now = timezone.now()
    for pk in sent:
        recipients[pk].sent_at = now
        recipients[pk].save(update_fields=['sent_at'])

    campaign.status = 'failed' if not sent else 'partial' if failed else 'sent'
    campaign.sent_at = now
    campaign.save(update_fields=['status', 'sent_at'])
    return len(sent), len(failed)


def send_html(to, subject, html_body):
    """E-mail individuel depuis l'adresse principale. Renvoie True s'il est parti."""
    message = EmailMultiAlternatives(
        subject=subject, body=strip_tags(html_body), from_email=settings.DEFAULT_FROM_EMAIL,
        to=[to], reply_to=[settings.DEFAULT_FROM_EMAIL])
    message.attach_alternative(html_body, 'text/html')
    try:
        return bool(message.send())
    except Exception:
        logger.exception("Échec de l'envoi de la réponse à %s", to)
        return False


send_reply = send_html  # réponse à un message de contact


def send_application_received(application):
    """Accusé de réception d'une demande d'adhésion."""
    html_body = render_to_string('emails/application_received.html', {'name': application.full_name})
    return send_html(application.email, "Votre demande d'adhésion à Zabantu", html_body)


def send_application_approved(application):
    """Annonce l'admission. L'adhésion ne donne pas accès au backoffice : le message ne parle pas de connexion."""
    html_body = render_to_string('emails/application_approved.html', {
        'name': application.full_name,
        'members_url': absolute_url(reverse('public_member_list')),
    })
    return send_html(application.email, 'Bienvenue chez Zabantu : votre adhésion est validée', html_body)


def send_access_granted(user):
    """Prévient un membre qu'il peut désormais se connecter ; lui propose de choisir un mot de passe s'il n'en a pas."""
    password_url = None
    if not user.has_usable_password():
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        password_url = absolute_url(reverse('password_reset_confirm', args=[uid, default_token_generator.make_token(user)]))
    html_body = render_to_string('emails/access_granted.html', {
        'name': user.get_full_name(),
        'password_url': password_url,
        'login_url': absolute_url(reverse('login')),
    })
    return send_html(user.email, "Votre accès à l'espace de gestion de Zabantu", html_body)
