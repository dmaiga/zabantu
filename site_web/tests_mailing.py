from datetime import timedelta
from io import StringIO
from unittest import mock

from django.core.management import call_command

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from articles.models import Article, Guelekan
from events.models import Event
from users.testing import make_user

from . import mailing
from .models import MembershipApplication, NewsletterCampaign, NewsletterRecipient, NewsletterSubscriber, PublicationDelivery, PublicationNotice


def subscribe(email, active=True):
    return NewsletterSubscriber.objects.create(email=email, is_active=active)


def make_article(**kw):
    defaults = dict(title='Étude sur le Sahel', status='published', content='<p>Un <b>long</b> texte.</p>',
                    resume='Résumé court.')
    defaults.update(kw)
    return Article.objects.create(**defaults)


class AnnouncementTests(TestCase):
    """La publication met l'annonce en file (signal) ; l'envoi par lots est fait par send_pending."""

    def setUp(self):
        self.active = subscribe('actif@test.org')
        subscribe('parti@test.org', active=False)

    def test_publishing_sends_nothing_by_itself(self):
        make_article()
        self.assertEqual(mail.outbox, [])
        self.assertEqual(PublicationDelivery.objects.count(), 1)

    def test_draft_is_not_queued(self):
        make_article(status='draft')
        self.assertFalse(PublicationNotice.objects.exists())

    def test_only_active_subscribers_receive_it_individually(self):
        make_article()
        self.assertEqual(mailing.send_pending(), (1, 0))
        self.assertEqual([m.to for m in mail.outbox], [['actif@test.org']])

    def test_publication_wording_is_neutral(self):
        make_article()
        mailing.send_pending()
        msg = mail.outbox[0]
        self.assertEqual(msg.subject, 'Nouvelle publication : Étude sur le Sahel')
        self.assertNotIn('article', (msg.subject + msg.body + msg.alternatives[0][0]).lower())

    def test_guelekan_is_announced_as_a_publication(self):
        Guelekan.objects.create(title='Séminaire', content='<p>x</p>', status='published')
        mailing.send_pending()
        self.assertEqual(mail.outbox[0].subject, 'Nouvelle publication : Séminaire')

    def test_upcoming_event_wording(self):
        Event.objects.create(title='Atelier', content='Contenu', image='x.jpg', status='published',
                             date=timezone.now() + timedelta(days=2))
        mailing.send_pending()
        self.assertEqual(mail.outbox[0].subject, 'Nouvel événement : Atelier')

    def test_past_event_is_not_announced(self):
        Event.objects.create(title='Passé', content='x', image='x.jpg', status='published',
                             date=timezone.now() - timedelta(days=2))
        self.assertFalse(PublicationNotice.objects.exists())
        self.assertEqual(mailing.send_pending(), (0, 0))
        self.assertEqual(mail.outbox, [])

    def test_content_is_announced_only_once(self):
        article = make_article()
        mailing.send_pending()
        article.title = 'Modifié'
        article.save()
        mailing.send_pending()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(PublicationNotice.objects.get().sent_count, 1)

    @override_settings(SEND_NEWSLETTER_ON_PUBLISH=False)
    def test_switch_off_queues_nothing(self):
        make_article()
        self.assertFalse(PublicationNotice.objects.exists())

    def test_links_use_the_token_and_the_public_page(self):
        article = make_article()
        mailing.send_pending()
        body = mail.outbox[0].body
        self.assertIn(reverse('public_article_detail', args=[article.slug]), body)
        self.assertIn(str(self.active.token), body)
        self.assertIn('List-Unsubscribe', mail.outbox[0].extra_headers)

    def test_failures_are_retried_on_the_next_run(self):
        make_article()
        with mock.patch.object(mailing.EmailMultiAlternatives, 'send', side_effect=OSError), \
                self.assertLogs('site_web.mailing', 'ERROR'):
            self.assertEqual(mailing.send_pending(), (0, 1))
        self.assertEqual(PublicationNotice.objects.get().sent_count, 0)
        self.assertEqual(mailing.send_pending(), (1, 0))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mailing.send_pending(), (0, 0))

    @override_settings(NEWSLETTER_MAX_ATTEMPTS=2)
    def test_gives_up_after_max_attempts(self):
        make_article()
        with mock.patch.object(mailing.EmailMultiAlternatives, 'send', side_effect=OSError), \
                self.assertLogs('site_web.mailing', 'ERROR'):
            mailing.send_pending()
            mailing.send_pending()
        self.assertEqual(mailing.send_pending(), (0, 0))
        self.assertEqual(mail.outbox, [])

    def test_unpublished_content_is_no_longer_announced(self):
        article = make_article()
        article.status = 'draft'
        article.save()
        self.assertEqual(mailing.send_pending(), (0, 0))
        self.assertEqual(mail.outbox, [])

    @override_settings(NEWSLETTER_BATCH_SIZE=2, NEWSLETTER_BATCH_PAUSE=7)
    def test_sends_in_batches_with_a_pause(self):
        for i in range(4):
            subscribe(f'n{i}@test.org')
        make_article()
        with mock.patch.object(mailing.time, 'sleep') as sleep, \
                mock.patch.object(mailing, '_deliver_batch', wraps=mailing._deliver_batch) as batch:
            self.assertEqual(mailing.send_pending(), (5, 0))
        self.assertEqual([len(c.args[0]) for c in batch.call_args_list], [2, 2, 1])
        self.assertEqual(sleep.call_args_list, [mock.call(7), mock.call(7)])

    def test_command_sends_pending(self):
        make_article()
        out = StringIO()
        call_command('send_pending_emails', stdout=out)
        self.assertIn('1 e-mail(s) envoyé(s)', out.getvalue())
        self.assertEqual(len(mail.outbox), 1)


class CampaignTests(TestCase):
    def setUp(self):
        self.sub_ok = subscribe('ok@test.org')
        self.sub_gone = subscribe('gone@test.org', active=False)
        self.campaign = NewsletterCampaign.objects.create(
            title='Voeux', subject='Bonne année', content='Bonjour\n\nÀ bientôt', created_by=make_user('admin'))
        for s in (self.sub_ok, self.sub_gone):
            NewsletterRecipient.objects.create(campaign=self.campaign, subscriber=s)

    def test_sends_to_active_recipients_with_a_readable_body(self):
        self.assertEqual(self.campaign.send(), (1, 0))
        msg = mail.outbox[0]
        self.assertEqual(msg.to, ['ok@test.org'])
        self.assertIn('Bonjour', msg.alternatives[0][0])
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.status, 'sent')
        self.assertIsNotNone(NewsletterRecipient.objects.get(subscriber=self.sub_ok).sent_at)

    def test_status_is_failed_when_nothing_goes_out(self):
        with mock.patch.object(mailing.EmailMultiAlternatives, 'send', side_effect=OSError), \
                self.assertLogs('site_web.mailing', 'ERROR'):
            self.assertEqual(self.campaign.send(), (0, 1))
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.status, 'failed')


class UnsubscribeTests(TestCase):
    def test_token_link_unsubscribes(self):
        sub = subscribe('x@test.org')
        url = reverse('newsletter_unsubscribe', args=[sub.token])
        self.assertEqual(self.client.get(url).status_code, 200)
        self.client.post(url)
        sub.refresh_from_db()
        self.assertFalse(sub.is_active)

    def test_numeric_id_no_longer_works(self):
        sub = subscribe('x@test.org')
        self.assertEqual(self.client.get(f'/zabantu/newsletter/unsubscribe/{sub.pk}/').status_code, 404)


class PublishViewTests(TestCase):
    def test_publishing_announces_and_republishing_does_not_repeat(self):
        subscribe('actif@test.org')
        self.client.force_login(make_user('moderateur'))
        article = make_article(status='draft')
        self.client.post(reverse('publish_article', args=[article.slug]))
        self.client.post(reverse('unpublish_article', args=[article.slug]))
        self.client.post(reverse('publish_article', args=[article.slug]))
        self.assertEqual(mail.outbox, [])  # la requête n'envoie rien
        mailing.send_pending()
        self.assertEqual(len(mail.outbox), 1)


class ScheduledPublicationTests(TestCase):
    def setUp(self):
        self.moderator = make_user('moderateur')
        self.client.force_login(self.moderator)
        subscribe('actif@test.org')

    def future(self, hours=2):
        return (timezone.localtime() + timedelta(hours=hours)).strftime('%Y-%m-%dT%H:%M')

    def test_scheduling_keeps_the_date_and_hides_the_content(self):
        article = make_article(status='draft')
        self.client.post(reverse('schedule_article', args=[article.slug]), {'publish_at': self.future()})
        article.refresh_from_db()
        self.assertEqual(article.status, 'scheduled')
        self.assertGreater(article.publish_at, timezone.now())
        self.assertEqual(self.client.get(reverse('public_article_detail', args=[article.slug])).status_code, 404)

    def test_past_or_missing_date_is_refused(self):
        article = make_article(status='draft')
        for value in (self.future(-2), ''):
            self.client.post(reverse('schedule_article', args=[article.slug]), {'publish_at': value})
        article.refresh_from_db()
        self.assertEqual(article.status, 'draft')

    def test_member_cannot_schedule(self):
        article = make_article(status='draft')
        self.client.force_login(make_user('membre'))
        r = self.client.post(reverse('schedule_article', args=[article.slug]), {'publish_at': self.future()})
        self.assertEqual(r.status_code, 403)

    def test_cancel_returns_to_draft(self):
        article = make_article(status='draft')
        self.client.post(reverse('schedule_article', args=[article.slug]), {'publish_at': self.future()})
        self.client.post(reverse('unpublish_article', args=[article.slug]))
        article.refresh_from_db()
        self.assertEqual((article.status, article.publish_at), ('draft', None))

    def test_command_publishes_due_items_and_announces_them_once(self):
        due = make_article(title='Echue', status='scheduled', publish_at=timezone.now() - timedelta(minutes=1))
        later = make_article(title='Plus tard', status='scheduled', publish_at=timezone.now() + timedelta(days=1))
        seminar = Guelekan.objects.create(title='Séminaire programmé', content='<p>x</p>', status='scheduled',
                                          publish_at=timezone.now() - timedelta(minutes=1))
        call_command('publish_scheduled', stdout=StringIO())
        call_command('publish_scheduled', stdout=StringIO())  # relancé par cron : rien de plus
        for obj in (due, later, seminar):
            obj.refresh_from_db()
        self.assertEqual((due.status, later.status, seminar.status), ('published', 'scheduled', 'published'))
        self.assertEqual(sorted(m.subject for m in mail.outbox),
                         ['Nouvelle publication : Echue', 'Nouvelle publication : Séminaire programmé'])

    def test_detail_pages_offer_scheduling_then_cancelling(self):
        article = make_article(status='draft')
        url = reverse('article_detail', args=[article.slug])
        self.assertContains(self.client.get(url), 'name="publish_at"')
        self.client.post(reverse('schedule_article', args=[article.slug]), {'publish_at': self.future()})
        self.assertContains(self.client.get(url), 'Annuler la programmation')
        seminar = Guelekan.objects.create(title='S', content='<p>x</p>', status='draft')
        self.assertContains(self.client.get(reverse('guelekan_detail', args=[seminar.slug])), 'name="publish_at"')

    def test_scheduled_without_a_date_falls_back_to_draft(self):
        self.assertEqual(make_article(status='scheduled', publish_at=None).status, 'draft')


class MembershipEmailTests(TestCase):
    def setUp(self):
        self.application = MembershipApplication.objects.create(
            full_name='Awa Diallo', email='awa@test.org', city_country='Bamako, Mali',
            academic_status='doctorant', institution='USJPB', research_interests='Sahel',
            contribution='x', career_benefit='y', consent=True)

    def test_received_acknowledgement(self):
        self.assertTrue(mailing.send_application_received(self.application))
        msg = mail.outbox[0]
        self.assertEqual(msg.to, ['awa@test.org'])
        self.assertIn('examiner votre dossier', msg.alternatives[0][0])

    def test_approval_email_welcomes_without_promising_a_login(self):
        self.application.approve(make_user('admin'))
        self.assertTrue(mailing.send_application_approved(self.application))
        html = mail.outbox[0].alternatives[0][0]
        self.assertIn('adhésion', html)
        self.assertNotIn('password', html.lower())
        self.assertNotIn('mot de passe', html.lower())

    def test_approved_member_does_not_get_backoffice_access(self):
        self.application.approve(make_user('admin'))
        self.assertFalse(self.application.member.backoffice_access)
        self.assertFalse(self.application.member.can_access_backoffice)

    def test_approving_from_the_backoffice_sends_the_welcome_email(self):
        self.client.force_login(make_user('moderateur'))
        self.client.post(reverse('membership_application_action', args=[self.application.pk, 'approve']))
        self.assertEqual([m.to for m in mail.outbox], [['awa@test.org']])
        self.assertIn('Bienvenue', mail.outbox[0].subject)

    def test_rejecting_sends_nothing(self):
        self.client.force_login(make_user('moderateur'))
        self.client.post(reverse('membership_application_action', args=[self.application.pk, 'reject']))
        self.assertEqual(mail.outbox, [])


class CampaignSendTests(TestCase):
    def test_sending_requires_post_and_a_moderator(self):
        campaign = NewsletterCampaign.objects.create(title='T', subject='S', content='c', created_by=make_user('admin'))
        url = reverse('newsletter_campaign_send', args=[campaign.pk])
        self.client.force_login(make_user('moderateur'))
        self.assertEqual(self.client.get(url).status_code, 405)
        self.client.force_login(make_user('membre'))
        self.assertEqual(self.client.post(url).status_code, 403)


class SeedDemoSafetyTests(TestCase):
    def test_refuses_to_mix_fake_data_into_a_database_with_real_content(self):
        from django.core.management import call_command
        from django.core.management.base import CommandError
        Article.objects.create(title='Vraie publication', content='x', status='published')
        with self.assertRaises(CommandError):
            call_command('seed_demo', stdout=StringIO())
        self.assertEqual(Article.objects.count(), 1)
