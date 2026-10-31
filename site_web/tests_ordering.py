from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from articles.models import Article, Guelekan
from events.models import Event
from users.testing import make_user


def publish(title, days_ago, **kw):
    """Publication dont la date de publication est `days_ago` jours dans le passé."""
    return Article.objects.create(title=title, status='published', content='x',
                                  publish_at=timezone.now() - timedelta(days=days_ago), **kw)


class PublicationOrderTests(TestCase):
    """Sur tout le site public, une publication se classe par sa date de publication, la plus récente d'abord."""

    def setUp(self):
        # créée en premier mais publiée en dernier : doit passer devant
        self.late_publication = publish('Rédigée tôt, publiée hier', days_ago=1)
        self.early_publication = publish('Rédigée tard, publiée il y a un mois', days_ago=30)
        self.middle = publish('Publiée il y a dix jours', days_ago=10)

    def titles(self, response, key='articles'):
        return [a.title for a in response.context[key]]

    def test_publications_page_sorts_by_publication_date_not_creation_date(self):
        r = self.client.get(reverse('public_article_list'))
        self.assertEqual(self.titles(r), ['Rédigée tôt, publiée hier', 'Publiée il y a dix jours',
                                          'Rédigée tard, publiée il y a un mois'])

    def test_oldest_first_option_reverses_it(self):
        r = self.client.get(reverse('public_article_list'), {'sort': 'date_asc'})
        self.assertEqual(self.titles(r)[0], 'Rédigée tard, publiée il y a un mois')
        self.assertEqual(self.titles(r)[-1], 'Rédigée tôt, publiée hier')

    def test_homepage_uses_the_same_order(self):
        r = self.client.get(reverse('home'))
        self.assertEqual(self.titles(r, 'latest_articles'),
                         ['Rédigée tôt, publiée hier', 'Publiée il y a dix jours', 'Rédigée tard, publiée il y a un mois'])

    def test_publication_without_a_date_goes_last_instead_of_first(self):
        undated = Article.objects.create(title='Sans date', status='published', content='x')
        Article.objects.filter(pk=undated.pk).update(publish_at=None)
        r = self.client.get(reverse('public_article_list'))
        self.assertEqual(self.titles(r)[-1], 'Sans date')

    def test_member_page_lists_their_publications_newest_first(self):
        author = make_user('membre')
        for article in (self.early_publication, self.late_publication, self.middle):
            article.authors.add(author)
        r = self.client.get(reverse('public_member_detail', args=[author.pk]))
        listed = [a.title for a in r.context['articles']]
        self.assertEqual(listed, ['Rédigée tôt, publiée hier', 'Publiée il y a dix jours',
                                  'Rédigée tard, publiée il y a un mois'])

    def test_guelekan_filter_sorts_the_same_way(self):
        Guelekan.objects.create(title='Ancien', content='<p>x</p>', status='published',
                                publish_at=timezone.now() - timedelta(days=40))
        Guelekan.objects.create(title='Récent', content='<p>x</p>', status='published',
                                publish_at=timezone.now() - timedelta(days=2))
        r = self.client.get(reverse('public_article_list'), {'type': 'guelekan'})
        self.assertEqual([g.title for g in r.context['guelekans']], ['Récent', 'Ancien'])

    def test_homepage_guelekans_newest_first(self):
        Guelekan.objects.create(title='Ancien', content='<p>x</p>', status='published',
                                publish_at=timezone.now() - timedelta(days=40))
        Guelekan.objects.create(title='Récent', content='<p>x</p>', status='published',
                                publish_at=timezone.now() - timedelta(days=2))
        r = self.client.get(reverse('home'))
        self.assertEqual([g.title for g in r.context['latest_guelekans']], ['Récent', 'Ancien'])


class EventOrderTests(TestCase):
    def setUp(self):
        now = timezone.now()
        for title, days in (('Passé récent', -5), ('Passé ancien', -60), ('Bientôt', 3), ('Plus tard', 40)):
            Event.objects.create(title=title, content='x', image='x.jpg', status='published',
                                 date=now + timedelta(days=days), event_type='conference')

    def test_past_events_newest_first(self):
        r = self.client.get(reverse('public_event_list'))
        self.assertEqual([e.title for e in r.context['past_events']], ['Passé récent', 'Passé ancien'])

    def test_upcoming_events_soonest_first(self):
        r = self.client.get(reverse('public_event_list'))
        self.assertEqual([e.title for e in r.context['upcoming_events']], ['Bientôt', 'Plus tard'])

    def test_homepage_upcoming_events_soonest_first(self):
        r = self.client.get(reverse('home'))
        self.assertEqual([e.title for e in r.context['upcoming_events']], ['Bientôt', 'Plus tard'])


class MemberDirectoryOrderTests(TestCase):
    def test_public_member_list_is_random_because_the_backoffice_sets_no_order(self):
        from django.contrib.auth import get_user_model
        U = get_user_model()
        for i, nom in enumerate(('Zongo', 'Adams', 'Mensah', 'Bah', 'Cissé', 'Diallo', 'Keita', 'Traoré')):
            U.objects.create_user(username=f'u{i}', email=f'u{i}@t.org', password='x', nom=nom, prenom='A', role='membre')
        orders = {tuple(m.pk for m in self.client.get(reverse('public_member_list')).context['members']) for _ in range(12)}
        self.assertGreater(len(orders), 1)                       # l'ordre change d'une visite à l'autre
        self.assertEqual(len({frozenset(o) for o in orders}), 1)  # mais ce sont toujours les mêmes membres
