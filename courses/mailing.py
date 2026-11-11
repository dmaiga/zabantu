"""E-mails des formations, chacun dans la langue du participant.

- send_confirmation(user)          : lien de confirmation de l'adresse (création du compte)
- send_decision(enrollment)        : inscription acceptée, refusée ou révoquée
- queue_open_cohorts() / send_pending_announcements() : ouverture d'une cohorte, envoyée par lots aux participants
  (appelées par la commande send_pending_emails, lancée par le cron toutes les 5 minutes)
"""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import EmailMultiAlternatives
from django.db.models import F
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone, translation
from django.utils.encoding import force_bytes
from django.utils.html import strip_tags
from django.utils.http import urlsafe_base64_encode
from django.utils.translation import gettext as _

from site_web import mailing as site_mailing
from zabantu.i18n import translated

from .models import Cohort, CohortAnnouncement, Enrollment


class ConfirmationTokenGenerator(PasswordResetTokenGenerator):
    """Jeton de confirmation d'adresse : il ne sert qu'une fois (l'état actif du compte entre dans le calcul)."""
    key_salt = 'courses.ConfirmationTokenGenerator'

    def _make_hash_value(self, user, timestamp):
        return f'{user.pk}{user.password}{user.is_active}{timestamp}{user.email}'


confirmation_token = ConfirmationTokenGenerator()


def _language(user):
    profile = getattr(user, 'participant_profile', None)
    return profile.language if profile else settings.LANGUAGE_CODE


def send_confirmation(user):
    language = _language(user)
    with translation.override(language):
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        url = site_mailing.absolute_url(reverse('participant_confirm', args=[uid, confirmation_token.make_token(user)]))
        html_body = render_to_string('courses/emails/confirm.html', {'name': user.get_full_name(), 'url': url})
        subject = _("Confirmez votre compte Zabantu")
    return site_mailing.send_html(user.email, subject, html_body)


def send_decision(enrollment):
    user = enrollment.user
    with translation.override(_language(user)):
        context = {
            'name': user.get_full_name(),
            'status': enrollment.status,
            'cohort': translated(enrollment.cohort, 'name'),
            'space_url': site_mailing.absolute_url(reverse('participant_space')),
            'courses': [translated(course, 'title') for course in enrollment.cohort.courses.all()],
        }
        subjects = {
            Enrollment.Status.ACCEPTED: _("Votre inscription à « %(cohort)s » est acceptée"),
            Enrollment.Status.REJECTED: _("Votre inscription à « %(cohort)s »"),
            Enrollment.Status.REVOKED: _("Votre accès à « %(cohort)s » a pris fin"),
        }
        subject = subjects[enrollment.status] % {'cohort': context['cohort']}
        html_body = render_to_string('courses/emails/decision.html', context)
    return site_mailing.send_html(user.email, subject, html_body)


def queue_open_cohorts():
    """Met en file l'annonce des cohortes ouvertes et pas encore annoncées, une fois par cohorte et par participant."""
    User = get_user_model()
    queued = 0
    for cohort in Cohort.objects.open().filter(announced_at=None):
        # Comptes participants, y compris ceux devenus membres (ils gardent leur profil participant)
        recipients = User.objects.filter(is_active=True, participant_profile__notify_cohorts=True)
        CohortAnnouncement.objects.bulk_create(
            [CohortAnnouncement(cohort=cohort, user=user) for user in recipients], ignore_conflicts=True)
        cohort.announced_at = timezone.now()
        cohort.save(update_fields=['announced_at'])
        queued += recipients.count()
    return queued


def _announcement_message(announcement):
    user, cohort = announcement.user, announcement.cohort
    with translation.override(_language(user)):
        context = {
            'name': user.get_full_name(),
            'cohort': translated(cohort, 'name'),
            'description': translated(cohort, 'description'),
            'closes_on': cohort.closes_on,
            'courses': [translated(course, 'title') for course in cohort.courses.all()],
            'url': site_mailing.absolute_url(reverse('training_list')),
            'settings_url': site_mailing.absolute_url(reverse('participant_space')),
        }
        subject = _("Nouvelle formation ouverte : %(cohort)s") % {'cohort': context['cohort']}
        html_body = render_to_string('courses/emails/cohort_opened.html', context)
    message = EmailMultiAlternatives(subject=subject, body=strip_tags(html_body),
                                     from_email=settings.DEFAULT_FROM_EMAIL_NEWS, to=[user.email])
    message.attach_alternative(html_body, 'text/html')
    return message


def send_pending_announcements():
    """Envoie par lots les annonces en attente (cohorte encore ouverte, participant toujours abonné). Renvoie (envoyés, échecs)."""
    queue_open_cohorts()
    pending = (CohortAnnouncement.objects
               .filter(sent_at=None, attempts__lt=settings.NEWSLETTER_MAX_ATTEMPTS, user__is_active=True,
                       user__participant_profile__notify_cohorts=True,
                       cohort__closes_on__gte=timezone.localdate())
               .select_related('user__participant_profile', 'cohort'))
    messages = {a.pk: _announcement_message(a) for a in pending}
    errors = {}
    sent, failed = site_mailing._deliver(messages, errors)
    CohortAnnouncement.objects.filter(pk__in=sent).update(sent_at=timezone.now(), attempts=F('attempts') + 1, last_error='')
    for pk in failed:
        CohortAnnouncement.objects.filter(pk=pk).update(attempts=F('attempts') + 1, last_error=errors.get(pk, ''))
    return len(sent), len(failed)
