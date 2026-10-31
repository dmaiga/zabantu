"""Données du tableau de bord, en trois temps : ce qui est à faire, ce qui se passe, ce qui s'est passé.

Un administrateur ou modérateur voit tout le site ; un membre autorisé ne voit que ses propres contenus."""
from datetime import timedelta

from django.contrib.contenttypes.models import ContentType
from django.db.models import Count
from django.urls import reverse
from django.utils import timezone

from articles.models import Article, Guelekan
from events.models import Event
from site_web.models import (ContactMessage, MembershipApplication, NewsletterCampaign, NewsletterSubscriber,
                             PublicationNotice)

from .models import CustomUser

SOON = timedelta(days=14)


def _item(count, label, hint, url, icon, tone, cta):
    return {'count': count, 'label': label, 'hint': hint, 'url': url, 'icon': icon, 'tone': tone, 'cta': cta}


def _plural(count, singular, plural):
    return singular if count == 1 else plural


def todo_items(user):
    """Ce qui attend une action, du plus urgent au moins urgent. Les éléments à zéro n'apparaissent pas."""
    now = timezone.now()
    items = []

    if user.can_moderate:
        soon_drafts = Event.objects.filter(status='draft', date__gte=now, date__lte=now + SOON).count()
        items.append(_item(
            soon_drafts, _plural(soon_drafts, 'événement proche encore en brouillon', 'événements proches encore en brouillon'),
            'Ils ont lieu dans les 14 jours : publiez-les pour que le public les voie.',
            reverse('event_list') + '?status=draft&when=upcoming', 'fa-calendar-xmark', 'danger', 'Voir'))

        seminars_without_guests = (Event.objects.filter(event_type='seminaire', date__gte=now)
                                   .annotate(n=Count('eventintervenant')).filter(n=0).count())
        items.append(_item(
            seminars_without_guests,
            _plural(seminars_without_guests, 'séminaire Gɛlɛkan à venir sans invité', 'séminaires Gɛlɛkan à venir sans invité'),
            "Ajoutez les professeurs et invités attendus.",
            reverse('event_list') + '?type=seminaire&when=upcoming', 'fa-microphone-lines', 'warning', 'Compléter'))

        pending = MembershipApplication.objects.filter(status=MembershipApplication.Status.PENDING).count()
        items.append(_item(
            pending, _plural(pending, "demande d'adhésion à examiner", "demandes d'adhésion à examiner"),
            "Les candidats attendent une réponse.",
            reverse('membership_application_list') + '?status=pending', 'fa-user-check', 'warning', 'Examiner'))

        unread = ContactMessage.objects.filter(is_read=False).count()
        items.append(_item(
            unread, _plural(unread, 'message non lu', 'messages non lus'),
            'Reçus depuis le formulaire de contact.',
            reverse('contact_message_list') + '?status=unread', 'fa-comments', 'warning', 'Lire'))

        drafts = Article.objects.filter(status='draft').count()
        items.append(_item(
            drafts, _plural(drafts, 'publication en brouillon', 'publications en brouillon'),
            'À relire, publier ou programmer.',
            reverse('article_list') + '?status=draft', 'fa-file-pen', 'secondary', 'Ouvrir'))

        seminar_drafts = Guelekan.objects.filter(status='draft').count()
        items.append(_item(
            seminar_drafts, _plural(seminar_drafts, 'Gɛlɛkan en brouillon', 'Gɛlɛkan en brouillon'),
            "Comptes rendus de séminaires à finaliser.",
            reverse('guelekan_list') + '?status=draft', 'fa-microphone-lines', 'secondary', 'Ouvrir'))

        campaigns = NewsletterCampaign.objects.filter(status='draft').count()
        items.append(_item(
            campaigns, _plural(campaigns, "campagne d'info-lettre en brouillon", "campagnes d'info-lettre en brouillon"),
            "Pas encore envoyées aux abonnés.",
            reverse('newsletter_campaign_list'), 'fa-envelope', 'secondary', 'Ouvrir'))
    else:
        mine = Article.objects.filter(authors=user, status='draft').count()
        items.append(_item(
            mine, _plural(mine, 'de vos publications en brouillon', 'de vos publications en brouillon'),
            'Terminez-les : un modérateur pourra ensuite les publier.',
            reverse('article_list') + '?status=draft', 'fa-file-pen', 'secondary', 'Ouvrir'))
        my_events = Event.objects.filter(author=user, status='draft', date__gte=now).count()
        items.append(_item(
            my_events, _plural(my_events, 'de vos événements à venir en brouillon', 'de vos événements à venir en brouillon'),
            'Ils ne sont pas encore visibles du public.',
            reverse('event_list') + '?status=draft&when=upcoming', 'fa-calendar-days', 'secondary', 'Ouvrir'))

    return [item for item in items if item['count']]


def current_state(user):
    """Les chiffres du moment, avec ce qui s'est ajouté depuis 30 jours."""
    now = timezone.now()
    month_ago = now - timedelta(days=30)
    members = CustomUser.objects.filter(is_active=True, role__in=['moderateur', 'membre'])
    stats = []

    if user.can_moderate:
        published = Article.objects.filter(status='published')
        stats += [
            ('Publications publiées', published.count(), published.filter(publish_at__gte=month_ago).count(), 'fa-file-lines'),
            ('Séminaires Gɛlɛkan', Guelekan.objects.filter(status='published').count(),
             Guelekan.objects.filter(status='published', publish_at__gte=month_ago).count(), 'fa-microphone-lines'),
            ('Événements à venir', Event.objects.filter(status='published', date__gte=now).count(), None, 'fa-calendar-days'),
            ('Membres', members.count(), members.filter(date_joined__gte=month_ago).count(), 'fa-users'),
            ("Abonnés à l'info-lettre", NewsletterSubscriber.objects.filter(is_active=True).count(),
             NewsletterSubscriber.objects.filter(is_active=True, subscribed_at__gte=month_ago).count(), 'fa-envelope'),
        ]
    else:
        mine = Article.objects.filter(authors=user)
        stats += [
            ('Vos publications publiées', mine.filter(status='published').count(), None, 'fa-file-lines'),
            ('Vos brouillons', mine.filter(status='draft').count(), None, 'fa-file-pen'),
            ('Événements à venir', Event.objects.filter(status='published', date__gte=now).count(), None, 'fa-calendar-days'),
        ]
    return [{'label': l, 'value': v, 'recent': r, 'icon': i} for l, v, r, i in stats]


def upcoming_events(user, limit=5):
    now = timezone.now()
    events = Event.objects.filter(date__gte=now).order_by('date')
    if not user.can_moderate:
        events = events.filter(status='published') | events.filter(author=user)
        events = events.order_by('date')
    return list(events.distinct()[:limit])


def scheduled_items(user):
    """Publications programmées, de la plus proche à la plus lointaine."""
    articles = Article.objects.filter(status='scheduled')
    seminars = Guelekan.objects.filter(status='scheduled')
    if not user.can_moderate:
        articles, seminars = articles.filter(authors=user), seminars.none()
    entries = [{'title': a.title, 'when': a.publish_at, 'url': reverse('article_detail', args=[a.slug])} for a in articles]
    entries += [{'title': g.title, 'when': g.publish_at, 'url': reverse('guelekan_detail', args=[g.slug])} for g in seminars]
    return sorted(entries, key=lambda e: e['when'])[:5]


def latest_received(user, limit=5):
    """Les dernières entrées reçues du public : messages, demandes d'adhésion, abonnés (modérateurs seulement)."""
    if not user.can_moderate:
        return None
    return {
        'messages': list(ContactMessage.objects.order_by('-created_at')[:limit]),
        'applications': list(MembershipApplication.objects.order_by('-created_at')[:limit]),
        'subscribers': list(NewsletterSubscriber.objects.order_by('-subscribed_at')[:limit]),
    }


def _announcement_title(notice):
    try:
        return ContentType.objects.get_for_id(notice.content_type_id).get_object_for_this_type(pk=notice.object_id).title
    except Exception:  # contenu supprimé depuis
        return 'contenu supprimé'


def recent_activity(user, limit=12):
    """Ce qui s'est passé récemment, du plus récent au plus ancien."""
    events = []

    def add(when, icon, text, url=None, tone='secondary'):
        if when:
            events.append({'when': when, 'icon': icon, 'text': text, 'url': url, 'tone': tone})

    if user.can_moderate:
        for a in Article.objects.filter(status='published').exclude(publish_at=None).order_by('-publish_at')[:5]:
            add(a.publish_at, 'fa-file-lines', f'Publication « {a.title} » publiée', reverse('article_detail', args=[a.slug]), 'success')
        for g in Guelekan.objects.filter(status='published').exclude(publish_at=None).order_by('-publish_at')[:3]:
            add(g.publish_at, 'fa-microphone-lines', f'Gɛlɛkan « {g.title} » publié', reverse('guelekan_detail', args=[g.slug]), 'success')
        for e in Event.objects.exclude(published_at=None).order_by('-published_at')[:4]:
            add(e.published_at, 'fa-calendar-days', f'Événement « {e.title} » publié', reverse('event_detail', args=[e.id]), 'success')
        for app in MembershipApplication.objects.order_by('-created_at')[:4]:
            add(app.created_at, 'fa-user-plus', f"Nouvelle demande d'adhésion de {app.full_name}",
                reverse('membership_application_detail', args=[app.pk]), 'warning')
        decided = MembershipApplication.objects.exclude(reviewed_at=None).select_related('reviewed_by').order_by('-reviewed_at')[:4]
        for app in decided:
            by = f' par {app.reviewed_by.get_full_name()}' if app.reviewed_by else ''
            verdict = {'approved': 'validée', 'rejected': 'refusée'}.get(app.status)
            if verdict:
                add(app.reviewed_at, 'fa-user-check', f'Adhésion de {app.full_name} {verdict}{by}',
                    reverse('membership_application_detail', args=[app.pk]), 'success' if verdict == 'validée' else 'secondary')
        for m in ContactMessage.objects.order_by('-created_at')[:4]:
            add(m.created_at, 'fa-comments', f'Message de {m.full_name} : {m.subject}',
                reverse('contact_message_detail', args=[m.pk]), 'warning' if not m.is_read else 'secondary')
        for sub in NewsletterSubscriber.objects.order_by('-subscribed_at')[:3]:
            add(sub.subscribed_at, 'fa-envelope', f"Nouvel abonné à l'info-lettre : {sub.email}", reverse('newsletter_list'))
        for notice in PublicationNotice.objects.filter(sent_count__gt=0).order_by('-created_at')[:3]:
            add(notice.created_at, 'fa-paper-plane',
                f'Annonce envoyée à {notice.sent_count} abonné(s) : « {_announcement_title(notice)} »', reverse('newsletter_list'))
        for c in NewsletterCampaign.objects.exclude(sent_at=None).order_by('-sent_at')[:3]:
            add(c.sent_at, 'fa-envelope-circle-check', f'Campagne « {c.title} » envoyée', reverse('newsletter_campaign_list'))
    else:
        for a in Article.objects.filter(authors=user, status='published').exclude(publish_at=None).order_by('-publish_at')[:6]:
            add(a.publish_at, 'fa-file-lines', f'Votre publication « {a.title} » a été publiée', reverse('article_detail', args=[a.slug]), 'success')
        for e in Event.objects.filter(author=user).order_by('-created_at')[:6]:
            add(e.created_at, 'fa-calendar-days', f'Vous avez créé l\'événement « {e.title} »', reverse('event_detail', args=[e.id]))

    return sorted(events, key=lambda e: e['when'], reverse=True)[:limit]
