"""Envoi des e-mails du site : un seul point d'entrée pour la connexion, le rendu et le journal.

- queue_publication(obj)  : met en file l'annonce d'une publication ou d'un événement (appelée par un signal)
- send_pending()           : envoie par lots les annonces en file et retente les échecs (commande send_pending_emails)
- send_campaign(campaign)  : envoie une campagne d'info-lettre à ses destinataires
- send_reply(...)          : réponse à un message de contact
"""
import html
import logging
import time

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db.models import F
from django.core.mail import EmailMultiAlternatives, get_connection
from django.contrib.auth.tokens import default_token_generator
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.html import strip_tags
from django.utils.http import urlsafe_base64_encode
from django.utils.text import Truncator

from .models import NewsletterSubscriber, PublicationDelivery, PublicationNotice

logger = logging.getLogger(__name__)

EXCERPT_FIELDS = ('resume', 'abstract', 'subtitle', 'content')


def absolute_url(path):
    return f"{settings.SITE_URL.rstrip('/')}{path}"


def unsubscribe_url(subscriber):
    return absolute_url(reverse('newsletter_unsubscribe', args=[subscriber.token]))


def newsletter_connection():
    """Connexion SMTP dédiée à l'info-lettre (le backend suit EMAIL_BACKEND : console en dev, mémoire en test)."""
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


def _short_error(exc):
    return f"{exc.__class__.__name__}: {exc}"[:255]


def _deliver_batch(batch, errors=None):
    """Envoie une liste de (clé, message) sur une connexion neuve ; renvoie (clés envoyées, clés en échec).

    `errors`, s'il est fourni, reçoit {clé: cause} pour chaque échec."""
    sent, failed = [], []
    errors = {} if errors is None else errors
    connection = newsletter_connection()
    try:
        connection.open()
    except Exception as exc:
        logger.exception("Connexion au serveur d'info-lettre impossible")
        errors.update({key: _short_error(exc) for key, _ in batch})
        return sent, [key for key, _ in batch]
    try:
        for key, message in batch:
            message.connection = connection
            try:
                delivered = message.send()
            except Exception as exc:
                logger.exception("Échec d'envoi à %s", message.to)
                errors[key] = _short_error(exc)
                delivered = 0
            if not delivered:
                errors.setdefault(key, "Le serveur n'a pas accepté le message")
            (sent if delivered else failed).append(key)
    finally:
        connection.close()
    return sent, failed


def _deliver(messages, errors=None):
    """Envoie {clé: message} par lots (NEWSLETTER_BATCH_SIZE), avec une pause entre deux lots (NEWSLETTER_BATCH_PAUSE).

    Chaque lot ouvre sa propre connexion : une coupure du serveur n'affecte que son lot et le débit reste sous les
    limites des hébergeurs. Renvoie (clés envoyées, clés en échec) ; `errors` reçoit {clé: cause} des échecs.
    """
    items = list(messages.items())
    size = max(1, settings.NEWSLETTER_BATCH_SIZE)
    sent, failed = [], []
    for start in range(0, len(items), size):
        if start:
            time.sleep(settings.NEWSLETTER_BATCH_PAUSE)
        batch_sent, batch_failed = _deliver_batch(items[start:start + size], errors)
        sent += batch_sent
        failed += batch_failed
    return sent, failed


def _excerpt(obj):
    for field in EXCERPT_FIELDS:
        text = html.unescape(strip_tags(getattr(obj, field, None) or '')).strip()
        if text:
            return Truncator(text).words(50)
    return ''


def _is_event(obj):
    return obj.__class__.__name__ == 'Event'


def queue_publication(obj):
    """Met en file l'annonce de `obj` aux abonnés actifs, une seule fois ; rien n'est envoyé ici (voir send_pending).

    Renvoie le nombre d'envois créés, ou None si rien n'est mis en file.
    """
    if not settings.SEND_NEWSLETTER_ON_PUBLISH:
        return None
    if _is_event(obj) and obj.date < timezone.now():
        return None  # inutile d'annoncer un événement déjà passé

    notice, created = PublicationNotice.objects.get_or_create(
        content_type=ContentType.objects.get_for_model(obj), object_id=obj.pk)
    if not created:
        return None
    PublicationDelivery.objects.bulk_create(
        PublicationDelivery(notice=notice, subscriber=s) for s in NewsletterSubscriber.objects.filter(is_active=True))
    return notice.deliveries.count()


def _publication_message(delivery, obj):
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
    return _build_message(delivery.subscriber, f"{label} : {obj.title}", 'emails/publication.html', context, text)


def send_pending():
    """Envoie par lots les annonces en attente et retente les échecs (jusqu'à NEWSLETTER_MAX_ATTEMPTS). Renvoie (envoyés, échecs)."""
    pending = (PublicationDelivery.objects
               .filter(sent_at=None, attempts__lt=settings.NEWSLETTER_MAX_ATTEMPTS, subscriber__is_active=True)
               .select_related('subscriber', 'notice'))
    contents, messages, notices = {}, {}, set()
    for delivery in pending:
        notice = delivery.notice
        if notice.pk not in contents:
            contents[notice.pk] = notice.content_object
        obj = contents[notice.pk]
        if obj is None or getattr(obj, 'status', 'published') != 'published':
            continue  # supprimé ou dépublié depuis : on n'annonce plus
        messages[delivery.pk] = _publication_message(delivery, obj)
        notices.add(notice.pk)

    errors = {}
    sent, failed = _deliver(messages, errors)
    now = timezone.now()
    PublicationDelivery.objects.filter(pk__in=sent).update(sent_at=now, attempts=F('attempts') + 1, last_error='')
    for pk in failed:
        PublicationDelivery.objects.filter(pk=pk).update(attempts=F('attempts') + 1, last_error=errors.get(pk, ''))
    for notice in PublicationNotice.objects.filter(pk__in=notices):
        notice.sent_count = notice.deliveries.exclude(sent_at=None).count()
        notice.save(update_fields=['sent_count'])
    return len(sent), len(failed)


def send_campaign(campaign):
    """Envoie la campagne aux destinataires actifs qui ne l'ont pas encore reçue et met à jour son statut.

    Rappelée sur une campagne partielle, elle ne renvoie qu'aux échecs. Renvoie (envoyés, échecs)."""
    campaign.status = 'sending'
    campaign.save(update_fields=['status'])

    recipients = {r.pk: r for r in campaign.recipients.select_related('subscriber')
                  .filter(subscriber__is_active=True, sent_at=None)}
    context = {'title': campaign.title, 'body': campaign.content}
    text = strip_tags(campaign.content)
    messages = {pk: _build_message(r.subscriber, campaign.subject, 'emails/campaign.html', context, text)
                for pk, r in recipients.items()}

    errors = {}
    sent, failed = _deliver(messages, errors)
    now = timezone.now()
    for pk in sent:
        recipients[pk].sent_at = now
        recipients[pk].attempts += 1
        recipients[pk].last_error = ''
        recipients[pk].save(update_fields=['sent_at', 'attempts', 'last_error'])
    for pk in failed:
        recipients[pk].attempts += 1
        recipients[pk].last_error = errors.get(pk, '')
        recipients[pk].save(update_fields=['attempts', 'last_error'])

    delivered = campaign.recipients.exclude(sent_at=None).exists()
    pending = campaign.recipients.filter(sent_at=None, subscriber__is_active=True).exists()
    campaign.status = 'failed' if not delivered else 'partial' if pending else 'sent'
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
