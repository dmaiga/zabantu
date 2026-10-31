from datetime import timedelta

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from articles.models import Article
from events.models import Event
from site_web.models import (
    BlockedSender, NewsletterCampaign, NewsletterRecipient, NewsletterSubscriber, PublicationDelivery,
    PublicationNotice)
from users.models import CustomUser

DEMO_DOMAIN = 'demo.zabantu.test'
PREFIX = '[démo] '

ERRORS = [
    "SMTPRecipientsRefused: 550 5.1.1 Boîte aux lettres introuvable",
    "SMTPServerDisconnected: Connexion fermée par le serveur",
    "TimeoutError: délai dépassé",
    "SMTPDataError: 554 Message refusé (suspecté spam)",
    "SMTPSenderRefused: 452 Quota d'envoi dépassé",
]

# (nom, actif, bloqué)
SUBSCRIBERS = [
    ('amina.traore', True, False), ('moussa.keita', True, False), ('fatou.diallo', True, False),
    ('ibrahim.coulibaly', True, False), ('awa.sangare', True, False), ('seydou.konate', True, False),
    ('mariam.cisse', True, False), ('oumar.bagayoko', True, False), ('kadiatou.sidibe', True, False),
    ('sekou.diarra', True, False), ('salimata.doumbia', False, False), ('bakary.camara', False, False),
    ('robot.spam1234', False, True), ('promo.gagnant99', False, True),
]


class Command(BaseCommand):
    help = (
        "Crée un jeu de démonstration pour l'info-lettre : abonnés (actifs, inactifs, bloqués), campagnes dans tous les "
        "états et annonces de publication reçues, en attente, en échec ou abandonnées. Les adresses sont en "
        f"@{DEMO_DOMAIN}. S'appuie sur les publications existantes (voir seed_demo)."
    )

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true', help="Supprime d'abord le jeu de démonstration existant.")
        parser.add_argument('--force', action='store_true',
                            help="Autorise l'exécution hors mode DEBUG (les envois en attente ne partiraient pas : adresses fictives).")

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG and not options['force']:
            raise CommandError("Jeu de démonstration réservé au développement (DEBUG=False). Utilisez --force si c'est voulu.")
        if options['reset']:
            self.reset()
        elif NewsletterSubscriber.objects.filter(email__endswith='@' + DEMO_DOMAIN).exists():
            raise CommandError("Le jeu de démonstration existe déjà. Relancez avec --reset pour le recréer.")

        author = (CustomUser.objects.filter(is_superuser=True).first()
                  or CustomUser.objects.filter(role__in=('admin', 'moderateur')).first())
        if not author:
            raise CommandError("Aucun administrateur trouvé pour signer les campagnes.")

        subscribers = self.seed_subscribers(author)
        self.seed_campaigns(author, [s for s in subscribers if s.is_active])
        notices = self.seed_deliveries(subscribers)
        self.stdout.write(self.style.SUCCESS(
            f'{len(subscribers)} abonnés, 6 campagnes et {notices} annonce(s) de publication créés. '
            'Voir /users/newsletter/ et /users/emails/.'))
        if not notices:
            self.stdout.write(self.style.WARNING(
                "Aucune publication publiée trouvée : lancez d'abord « python manage.py seed_demo » pour voir la page Envois e-mail."))

    def reset(self):
        NewsletterSubscriber.objects.filter(email__endswith='@' + DEMO_DOMAIN).delete()
        BlockedSender.objects.filter(email__endswith='@' + DEMO_DOMAIN).delete()
        NewsletterCampaign.objects.filter(title__startswith=PREFIX).delete()
        PublicationNotice.objects.filter(deliveries__isnull=True).delete()
        self.stdout.write('Jeu de démonstration supprimé.')

    def seed_subscribers(self, author):
        now = timezone.now()
        subscribers = []
        for i, (name, active, blocked) in enumerate(SUBSCRIBERS):
            email = f'{name}@{DEMO_DOMAIN}'
            sub = NewsletterSubscriber.objects.create(email=email, is_active=active)
            NewsletterSubscriber.objects.filter(pk=sub.pk).update(subscribed_at=now - timedelta(days=3 * i + 1, hours=i))
            sub.refresh_from_db()
            if blocked:
                BlockedSender.objects.get_or_create(email=email, defaults={'blocked_by': author})
            subscribers.append(sub)
        return subscribers

    def seed_campaigns(self, author, active):
        now = timezone.now()

        def campaign(title, subject, body, status, sent_ago=None):
            c = NewsletterCampaign.objects.create(
                title=PREFIX + title, subject=subject, content=body, status=status, created_by=author,
                sent_at=now - sent_ago if sent_ago else None)
            return c

        def recipients(c, subs, outcome):
            """outcome(i) -> 'sent' | 'failed' | 'pending'."""
            for i, sub in enumerate(subs):
                state = outcome(i)
                NewsletterRecipient.objects.create(
                    campaign=c, subscriber=sub,
                    sent_at=(c.sent_at or now) if state == 'sent' else None,
                    attempts=0 if state == 'pending' else 1 + (i % 2),
                    last_error=ERRORS[i % len(ERRORS)] if state == 'failed' else '')

        c = campaign('Appel à communications 2026', "Appel à communications : colloque Zabantu 2026",
                     '<p>Chères et chers collègues,</p><p>Nous lançons l\'<strong>appel à communications</strong> du colloque 2026.</p>',
                     'draft')
        recipients(c, active, lambda i: 'pending')

        c = campaign('Rentrée scientifique', 'Notre programme de rentrée',
                     '<p>Bonne rentrée à toutes et tous !</p><ul><li>Séminaire mensuel</li><li>Nouvelle revue en ligne</li></ul>',
                     'sent', timedelta(days=12))
        recipients(c, active, lambda i: 'sent')

        c = campaign('Numéro spécial : migrations', 'Nouveau numéro : migrations et mobilités',
                     '<p>Le numéro spécial sur les <em>migrations</em> est en ligne.</p>', 'partial', timedelta(days=3))
        recipients(c, active, lambda i: 'failed' if i in (2, 5, 7) else 'sent')

        c = campaign('Vœux de fin d\'année', 'Bonne année 2027', '<p>Toute l\'équipe vous souhaite une excellente année.</p>',
                     'failed', timedelta(days=1))
        recipients(c, active, lambda i: 'failed')

        c = campaign('Rappel inscription', 'Dernier rappel : inscriptions ouvertes', '<p>Les inscriptions ferment vendredi.</p>',
                     'sending', timedelta(minutes=2))
        recipients(c, active, lambda i: 'sent' if i < 4 else 'pending')

        c = campaign('Enquête (annulée)', 'Enquête auprès des membres', '<p>Cette enquête a été reportée.</p>', 'cancelled')
        recipients(c, active, lambda i: 'pending')

    def seed_deliveries(self, subscribers):
        now = timezone.now()
        limit = settings.NEWSLETTER_MAX_ATTEMPTS
        active = [s for s in subscribers if s.is_active]
        objects = [o for o in list(Article.objects.filter(status='published').order_by('-publish_at')[:4]) +
                   list(Event.objects.filter(status='published').order_by('-date')[:2])
                   if not PublicationNotice.objects.filter(
                       content_type=ContentType.objects.get_for_model(o), object_id=o.pk).exists()][:5]

        # une annonce par scénario : tout reçu, en attente, échecs en cours de nouvelle tentative, abandons, mélange
        scenarios = [
            lambda i: ('sent', 1, ''),
            lambda i: ('pending', 0, ''),
            lambda i: ('failed', 1 + i % 3, ERRORS[i % len(ERRORS)]) if i % 3 == 0 else ('sent', 1, ''),
            lambda i: ('failed', limit, ERRORS[i % len(ERRORS)]) if i % 2 == 0 else ('sent', 1, ''),
            lambda i: ('sent', 1, '') if i < 4 else ('pending', 0, '') if i < 7 else ('failed', 2, ERRORS[i % len(ERRORS)]),
        ]
        for n, obj in enumerate(objects):
            notice = PublicationNotice.objects.create(
                content_type=ContentType.objects.get_for_model(obj), object_id=obj.pk)
            PublicationNotice.objects.filter(pk=notice.pk).update(created_at=now - timedelta(days=n, hours=2 * n))
            for i, sub in enumerate(active):
                state, attempts, error = scenarios[n % len(scenarios)](i)
                PublicationDelivery.objects.create(
                    notice=notice, subscriber=sub, attempts=attempts, last_error=error,
                    sent_at=now - timedelta(days=n, hours=2 * n - 1) if state == 'sent' else None)
            notice.sent_count = notice.deliveries.exclude(sent_at=None).count()
            notice.save(update_fields=['sent_count'])
        return len(objects)
