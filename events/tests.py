from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from users.testing import make_user

from .models import Event


def make_event(**kw):
    defaults = dict(title='Atelier test', content='Contenu', image='events/x.jpg',
                    date=timezone.now() + timedelta(days=3), status='draft')
    defaults.update(kw)
    return Event.objects.create(**defaults)


class EventListFilterTests(TestCase):
    def setUp(self):
        self.client.force_login(make_user('admin'))
        make_event(title='Brouillon', status='draft')
        make_event(title='En ligne', status='published')

    def test_status_filter_does_not_crash_and_filters(self):
        r = self.client.get(reverse('event_list'), {'status': 'published'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual([e.title for e in r.context['events']], ['En ligne'])

    def test_unknown_status_and_type_are_ignored(self):
        r = self.client.get(reverse('event_list'), {'status': 'nope', 'type': 'nope'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.context['events']), 2)

    def test_invalid_sort_falls_back_to_default(self):
        r = self.client.get(reverse('event_list'), {'sort': 'author__password'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context['current_sort'], '-date')


class EventPermissionTests(TestCase):
    def setUp(self):
        self.event = make_event()
        self.member = make_user('membre')
        self.moderator = make_user('moderateur')

    def test_member_cannot_publish_unpublish_archive_or_delete(self):
        self.client.force_login(self.member)
        for name in ('event_publish', 'event_unpublish', 'event_archive'):
            r = self.client.post(reverse(name, args=[self.event.id]))
            self.assertEqual(r.status_code, 403, name)
        self.assertEqual(self.client.post(reverse('event_delete', args=[self.event.id])).status_code, 403)
        self.event.refresh_from_db()
        self.assertEqual(self.event.status, 'draft')

    def test_publication_requires_post(self):
        self.client.force_login(self.moderator)
        r = self.client.get(reverse('event_publish', args=[self.event.id]))
        self.assertEqual(r.status_code, 405)
        self.event.refresh_from_db()
        self.assertEqual(self.event.status, 'draft')

    def test_moderator_can_publish_and_delete(self):
        self.client.force_login(self.moderator)
        self.client.post(reverse('event_publish', args=[self.event.id]))
        self.event.refresh_from_db()
        self.assertEqual(self.event.status, 'published')
        self.client.post(reverse('event_delete', args=[self.event.id]))
        self.assertFalse(Event.objects.filter(pk=self.event.pk).exists())

    def test_anonymous_is_sent_to_login(self):
        r = self.client.post(reverse('event_publish', args=[self.event.id]))
        self.assertEqual(r.status_code, 302)
        self.assertIn('/auth/', r.url)
