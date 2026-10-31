from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from articles.models import Article
from events.models import Event, EventIntervenant
from intervenants.models import Intervenant
from site_web.models import ContactMessage, MembershipApplication, NewsletterSubscriber
from users import dashboard_data
from users.testing import make_user


def event(title, days, **kw):
    return Event.objects.create(title=title, content='x', image='x.jpg', date=timezone.now() + timedelta(days=days), **kw)


def application(name='Awa Diallo', **kw):
    return MembershipApplication.objects.create(
        full_name=name, email=f'{name.split()[0].lower()}@t.org', city_country='Bamako', academic_status='doctorant',
        institution='U', research_interests='x', contribution='x', career_benefit='x', consent=True, **kw)


class TodoTests(TestCase):
    def setUp(self):
        self.moderator = make_user('moderateur')

    def todo(self, user=None):
        return {i['label']: i['count'] for i in dashboard_data.todo_items(user or self.moderator)}

    def test_empty_site_has_nothing_to_do(self):
        self.assertEqual(dashboard_data.todo_items(self.moderator), [])

    def test_counts_what_is_waiting(self):
        application()
        application('Moussa Traoré')
        ContactMessage.objects.create(name='A', last_name='B', email='a@b.org', subject='S', message='m')
        Article.objects.create(title='Brouillon', content='x')
        todo = self.todo()
        self.assertEqual(todo["demandes d'adhésion à examiner"], 2)
        self.assertEqual(todo['message non lu'], 1)
        self.assertEqual(todo['publication en brouillon'], 1)

    def test_decided_applications_are_no_longer_pending(self):
        application(status=MembershipApplication.Status.APPROVED)
        self.assertEqual(self.todo(), {})

    def test_urgent_items_come_first(self):
        Article.objects.create(title='Brouillon', content='x')
        application()
        event('Bientôt', 5, status='draft')
        labels = [i['label'] for i in dashboard_data.todo_items(self.moderator)]
        self.assertEqual(labels[0], 'événement proche encore en brouillon')
        self.assertEqual(labels[-1], 'publication en brouillon')

    def test_event_far_in_the_future_is_not_urgent(self):
        event('Dans trois mois', 90, status='draft')
        self.assertNotIn('événement proche encore en brouillon', self.todo())

    def test_gelekan_without_guests_is_flagged_until_a_guest_is_added(self):
        seminar = event('Séminaire', 20, status='published', event_type='seminaire')
        self.assertEqual(self.todo()['séminaire Gɛlɛkan à venir sans invité'], 1)
        guest = Intervenant.objects.create(first_name='A', last_name='B', email='g@t.org', organization='O',
                                           bio='b', intervenant_type='speaker')
        EventIntervenant.objects.create(event=seminar, intervenant=guest, role='speaker')
        self.assertNotIn('séminaire Gɛlɛkan à venir sans invité', self.todo())

    def test_every_item_links_somewhere_useful(self):
        application()
        item = dashboard_data.todo_items(self.moderator)[0]
        self.assertIn(reverse('membership_application_list'), item['url'])
        self.assertIn('status=pending', item['url'])


class MemberViewTests(TestCase):
    def setUp(self):
        self.member = make_user('membre')
        self.other = make_user('membre')

    def test_member_only_sees_their_own_work(self):
        Article.objects.create(title='Le mien', content='x').authors.add(self.member)
        Article.objects.create(title='Celui des autres', content='x').authors.add(self.other)
        items = dashboard_data.todo_items(self.member)
        self.assertEqual([(i['count'], i['label']) for i in items], [(1, 'de vos publications en brouillon')])

    def test_member_gets_no_admin_data(self):
        application()
        ContactMessage.objects.create(name='Secret', last_name='X', email='s@t.org', subject='Confidentiel', message='m')
        NewsletterSubscriber.objects.create(email='abonne-prive@t.org')
        self.client.force_login(self.member)
        html = self.client.get(reverse('dashboard')).content.decode()
        for private in ('Confidentiel', 'abonne-prive@t.org', "demande d'adhésion", 'Abonnés'):
            self.assertNotIn(private, html)
        self.assertEqual(self.client.get(reverse('dashboard')).status_code, 200)

    def test_member_activity_is_limited_to_their_content(self):
        mine = Article.objects.create(title='Le mien', content='x', status='published'); mine.authors.add(self.member)
        theirs = Article.objects.create(title='Celui des autres', content='x', status='published'); theirs.authors.add(self.other)
        texts = ' '.join(e['text'] for e in dashboard_data.recent_activity(self.member))
        self.assertIn('Le mien', texts)
        self.assertNotIn('Celui des autres', texts)


class ActivityTests(TestCase):
    def setUp(self):
        self.moderator = make_user('moderateur')

    def test_feed_mixes_sources_newest_first(self):
        old = Article.objects.create(title='Ancienne', content='x', status='published',
                                     publish_at=timezone.now() - timedelta(days=5))
        application('Awa Diallo')
        ContactMessage.objects.create(name='Doe', last_name='Jane', email='j@t.org', subject='Question', message='m')
        feed = dashboard_data.recent_activity(self.moderator)
        times = [e['when'] for e in feed]
        self.assertEqual(times, sorted(times, reverse=True))
        texts = [e['text'] for e in feed]
        self.assertTrue(any('Awa Diallo' in t for t in texts))
        self.assertTrue(any('Question' in t for t in texts))
        self.assertEqual(texts[-1], 'Publication « Ancienne » publiée')

    def test_decisions_are_attributed(self):
        app = application('Awa Diallo')
        app.approve(self.moderator)
        texts = [e['text'] for e in dashboard_data.recent_activity(self.moderator)]
        self.assertTrue(any(t.startswith('Adhésion de Awa Diallo validée par') for t in texts))

    def test_feed_is_capped(self):
        for i in range(30):
            application(f'Candidat{i} Test')
        self.assertLessEqual(len(dashboard_data.recent_activity(self.moderator)), 12)


class DashboardPageTests(TestCase):
    def test_page_renders_all_three_moments(self):
        user = make_user('moderateur')
        self.client.force_login(user)
        application()
        event('Conférence', 4, status='published')
        r = self.client.get(reverse('dashboard'))
        self.assertContains(r, 'À traiter maintenant')
        self.assertContains(r, 'Prochains événements')
        self.assertContains(r, 'Activité récente')
        self.assertContains(r, 'Conférence')

    def test_empty_state_reassures(self):
        self.client.force_login(make_user('moderateur'))
        self.assertContains(self.client.get(reverse('dashboard')), 'Tout est à jour')

    def test_stats_count_recent_additions(self):
        user = make_user('moderateur')
        Article.objects.create(title='Récente', content='x', status='published', publish_at=timezone.now() - timedelta(days=3))
        Article.objects.create(title='Ancienne', content='x', status='published', publish_at=timezone.now() - timedelta(days=90))
        stats = {s['label']: s for s in dashboard_data.current_state(user)}
        self.assertEqual((stats['Publications publiées']['value'], stats['Publications publiées']['recent']), (2, 1))

    def test_scheduled_publications_are_listed_soonest_first(self):
        user = make_user('moderateur')
        Article.objects.create(title='Plus tard', content='x', status='scheduled', publish_at=timezone.now() + timedelta(days=9))
        Article.objects.create(title='Demain', content='x', status='scheduled', publish_at=timezone.now() + timedelta(days=1))
        self.assertEqual([e['title'] for e in dashboard_data.scheduled_items(user)], ['Demain', 'Plus tard'])


class PresentationTests(TestCase):
    def test_durations_are_short_and_use_one_unit(self):
        from users.templatetags.ui_tags import since_short, until_short
        now = timezone.now()
        self.assertEqual(since_short(now - timedelta(minutes=15, seconds=5)), '15 min')
        self.assertEqual(since_short(now - timedelta(hours=2, minutes=20)), '2 h')
        self.assertEqual(since_short(now - timedelta(days=3, hours=5)), '3 j')
        self.assertEqual(since_short(now - timedelta(days=21)), '3 sem.')
        self.assertEqual(until_short(now + timedelta(days=4, hours=6, minutes=1)), '4 j')

    def test_announcements_that_reached_nobody_stay_out_of_the_feed(self):
        user = make_user('moderateur')
        article = Article.objects.create(title='Sans abonnés', content='x', status='published')
        from site_web import mailing
        mailing.send_pending()  # aucun abonné : l'annonce est notée mais n'a touché personne
        texts = [e['text'] for e in dashboard_data.recent_activity(user)]
        self.assertFalse(any('Annonce envoyée' in t for t in texts))
        NewsletterSubscriber.objects.create(email='lecteur@t.org')
        other = Article.objects.create(title='Avec abonné', content='x', status='published')
        mailing.send_pending()
        texts = [e['text'] for e in dashboard_data.recent_activity(user)]
        self.assertTrue(any('Annonce envoyée à 1 abonné' in t for t in texts))


class DashboardLayoutTests(TestCase):
    def setUp(self):
        self.moderator = make_user('moderateur')
        self.client.force_login(self.moderator)

    def html(self):
        return self.client.get(reverse('dashboard')).content.decode()

    def test_key_figures_come_first(self):
        html = self.html()
        self.assertLess(html.index('Publications publiées'), html.index('À traiter maintenant'))
        self.assertLess(html.index('À traiter maintenant'), html.index('Prochains événements'))

    def test_no_greeting_and_no_filler_sentence(self):
        html = self.html()
        self.assertNotIn('Bonjour', html)
        self.assertNotIn('Voici où en est le site', html)

    def test_activity_is_a_closed_accordion(self):
        html = self.html()
        self.assertIn('accordion-button collapsed', html)
        self.assertIn('aria-expanded="false"', html)
        panel = html.split('id="activityPanel"')[1][:80]
        self.assertIn('accordion-collapse collapse"', panel)
        self.assertNotIn(' show', panel)

    def test_latest_messages_applications_and_subscribers_are_back(self):
        ContactMessage.objects.create(name='Doe', last_name='Jane', email='j@t.org', subject='Question sur Gɛlɛkan', message='m')
        application('Awa Diallo')
        NewsletterSubscriber.objects.create(email='lecteur@t.org')
        html = self.html()
        for text in ('Derniers messages', 'Doe Jane', 'Question sur Gɛlɛkan',
                     "Dernières demandes d'adhésion", 'Awa Diallo', 'En attente',
                     "Derniers abonnés à l'info-lettre", 'lecteur@t.org', '>Non lu</span>'):
            self.assertIn(text, html, text)

    def test_message_status_badges(self):
        ContactMessage.objects.create(name='A', last_name='B', email='a@b.org', subject='Lu', message='m', is_read=True)
        ContactMessage.objects.create(name='C', last_name='D', email='c@d.org', subject='Répondu', message='m', replied=True)
        ContactMessage.objects.create(name='E', last_name='F', email='e@f.org', subject='Neuf', message='m')
        html = self.html()
        for badge in ('Non lu', 'Lu', 'Répondu'):
            self.assertIn(f'>{badge}</span>', html, badge)

    def test_members_do_not_get_the_received_section(self):
        ContactMessage.objects.create(name='Secret', last_name='X', email='s@t.org', subject='Confidentiel', message='m')
        self.client.force_login(make_user('membre'))
        html = self.html()
        self.assertNotIn('Derniers messages', html)
        self.assertNotIn('Confidentiel', html)
