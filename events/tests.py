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
        self.assertEqual([e.title for e in r.context['page_obj']], ['En ligne'])

    def test_unknown_status_and_type_are_ignored(self):
        r = self.client.get(reverse('event_list'), {'status': 'nope', 'type': 'nope'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.context['page_obj']), 2)

    def test_invalid_sort_falls_back_to_default(self):
        r = self.client.get(reverse('event_list'), {'sort': 'author__password'})
        self.assertEqual(r.status_code, 200)
        dates = [e.date for e in r.context['page_obj']]
        self.assertEqual(dates, sorted(dates, reverse=True))


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


class EventListPageTests(TestCase):
    def setUp(self):
        self.client.force_login(make_user('moderateur'))
        for i in range(23):
            make_event(title=f'Rencontre {i:02d}', status='published' if i % 2 else 'draft',
                       event_type='conference' if i % 3 else 'seminaire',
                       date=timezone.now() + timedelta(days=i - 10))

    def test_single_paginated_table_without_grid_toggle(self):
        r = self.client.get(reverse('event_list'))
        self.assertEqual(len(r.context['page_obj']), 20)
        self.assertNotContains(r, 'viewGrid')

    def test_period_status_and_type_filters(self):
        upcoming = self.client.get(reverse('event_list'), {'when': 'upcoming'}).context['page_obj'].paginator.count
        past = self.client.get(reverse('event_list'), {'when': 'past'}).context['page_obj'].paginator.count
        self.assertEqual(upcoming + past, 23)
        r = self.client.get(reverse('event_list'), {'status': 'published', 'type': 'conference'})
        self.assertTrue(all(e.status == 'published' and e.event_type == 'conference' for e in r.context['page_obj']))

    def test_list_offers_no_delete_but_detail_does(self):
        event = Event.objects.first()
        self.assertNotContains(self.client.get(reverse('event_list')), reverse('event_delete', args=[event.id]))
        self.assertContains(self.client.get(reverse('event_detail', args=[event.id])), reverse('event_delete', args=[event.id]))

    def test_sort_oldest_first(self):
        r = self.client.get(reverse('event_list'), {'sort': 'date'})
        dates = [e.date for e in r.context['page_obj']]
        self.assertEqual(dates, sorted(dates))
