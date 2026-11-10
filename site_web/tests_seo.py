import datetime

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from articles.models import Article, Guelekan
from events.models import Event
from gallery.models import Gallery, Photo
from users.testing import make_user

START = datetime.date(2026, 11, 1)


def at(day, hour=12):
    return timezone.make_aware(datetime.datetime.combine(day, datetime.time(hour)))


@override_settings(SEO_START_DATE=START, SITE_URL='https://zabantu.net')
class SeoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = make_user('g')
        cls.old = Article.objects.create(title='Ancienne', article_type='analyse', status='published',
                                         content='<p>Texte <b>ancien</b></p>')
        Article.objects.filter(pk=cls.old.pk).update(publish_at=at(datetime.date(2026, 5, 1)))
        cls.new = Article.objects.create(title='Nouvelle', article_type='analyse', status='published',
                                         content='<p>Texte   <b>récent</b></p>', meta_description='Résumé SEO')
        Article.objects.filter(pk=cls.new.pk).update(publish_at=at(START))
        cls.draft = Article.objects.create(title='Brouillon', article_type='analyse', status='draft', content='x')
        cls.future = Article.objects.create(title='Future', article_type='analyse', status='published', content='x')
        Article.objects.filter(pk=cls.future.pk).update(publish_at=timezone.now() + datetime.timedelta(days=3))
        cls.event_new = Event.objects.create(title='Évt récent', content='<p>Programme</p>', image='events/x.png',
                                             status='published', date=timezone.now() + datetime.timedelta(days=2),
                                             author=cls.user)
        cls.event_old = Event.objects.create(title='Évt ancien', content='x', image='events/x.png',
                                             status='published', date=timezone.now() + datetime.timedelta(days=2),
                                             author=cls.user)
        Event.objects.filter(pk=cls.event_old.pk).update(created_at=at(datetime.date(2026, 3, 1)))

    def page(self, article):
        return self.client.get(reverse('public_article_detail', args=[article.slug])).content.decode()

    def test_every_page_has_share_tags_with_absolute_urls(self):
        html = self.client.get(reverse('home')).content.decode()
        for needle in ('property="og:title"', 'property="og:site_name" content="Zabantu"', 'content="fr_FR"',
                       'content="https://zabantu.net/static/site_web/images/og-default.jpg"',
                       'name="twitter:card" content="summary_large_image"'):
            self.assertIn(needle, html, needle)
        self.assertIn('rel="canonical" href="https://zabantu.net/zabantu/"', html)

    def test_root_redirects_to_the_canonical_home_in_each_language(self):
        self.assertRedirects(self.client.get('/'), '/zabantu/', status_code=301, fetch_redirect_response=False)
        self.assertRedirects(self.client.get('/en/'), '/en/zabantu/', status_code=301,
                             fetch_redirect_response=False)

    def test_old_article_gets_share_tags_but_no_canonical(self):
        html = self.page(self.old)
        self.assertIn('property="og:title" content="Ancienne"', html)
        self.assertIn('property="og:description" content="Texte ancien"', html)  # HTML retiré
        self.assertNotIn('rel="canonical"', html)

    def test_new_article_has_canonical_description_and_type(self):
        html = self.page(self.new)
        self.assertIn('rel="canonical" href="https://zabantu.net/zabantu/publications/', html)
        self.assertIn('property="og:description" content="Résumé SEO"', html)
        self.assertIn('property="og:type" content="article"', html)
        self.assertIn('article:published_time', html)

    def test_event_pages(self):
        new = self.client.get(reverse('public_event_detail', args=[self.event_new.pk])).content.decode()
        old = self.client.get(reverse('public_event_detail', args=[self.event_old.pk])).content.decode()
        self.assertIn('rel="canonical"', new)
        self.assertNotIn('rel="canonical"', old)
        self.assertIn('property="og:title" content="Évt ancien"', old)

    def test_unpublished_pages_stay_hidden(self):
        self.assertEqual(self.client.get(reverse('public_article_detail', args=[self.draft.slug])).status_code, 404)
        self.assertEqual(self.client.get(reverse('public_article_detail', args=[self.future.slug])).status_code, 404)

    def test_sitemap_lists_only_new_published_content(self):
        r = self.client.get('/sitemap.xml')
        self.assertEqual(r.status_code, 200)
        self.assertIn('application/xml', r['Content-Type'])
        xml = r.content.decode()
        self.assertIn(f'https://zabantu.net/zabantu/publications/{self.new.slug}/', xml)
        self.assertIn(f'https://zabantu.net/zabantu/evenements/{self.event_new.pk}/', xml)
        for excluded in (self.old.slug, self.draft.slug, self.future.slug):
            self.assertNotIn(excluded, xml)
        self.assertNotIn(f'/zabantu/evenements/{self.event_old.pk}/', xml)
        for path in ('/zabantu/', '/zabantu/publications/', '/zabantu/evenements/', '/zabantu/membres/',
                     '/zabantu/galeries/', '/zabantu/about/'):
            self.assertIn(f'<loc>https://zabantu.net{path}</loc>', xml)

    def test_sitemap_uses_created_at_for_a_published_guelekan_without_publish_at(self):
        guelekan = Guelekan.objects.create(title='Compte-rendu', content='Texte', status='published')
        Guelekan.objects.filter(pk=guelekan.pk).update(publish_at=None, created_at=at(START))
        xml = self.client.get('/sitemap.xml').content.decode()
        self.assertIn(f'https://zabantu.net/zabantu/guelekans/{guelekan.slug}/', xml)

    def test_photo_title_uses_album_when_the_stored_title_is_a_raw_filename(self):
        gallery = Gallery.objects.create(title='Atelier de Bamako')
        raw = Photo.objects.create(gallery=gallery, title='IMG-20240803-WA0047.jpg', image='photos/raw.jpg')
        descriptive = Photo.objects.create(gallery=gallery, title='Présentation des résultats',
                                           image='photos/titled.jpg')
        raw_html = self.client.get(reverse('detail_photo', args=[raw.pk])).content.decode()
        titled_html = self.client.get(reverse('detail_photo', args=[descriptive.pk])).content.decode()
        self.assertIn('<title>Atelier de Bamako – Photo | Zabantu</title>', raw_html)
        self.assertIn('<title>Présentation des résultats – Atelier de Bamako | Zabantu</title>', titled_html)

    def test_robots_blocks_only_private_areas(self):
        r = self.client.get('/robots.txt')
        self.assertEqual(r.status_code, 200)
        text = r.content.decode()
        self.assertIn('Sitemap: https://zabantu.net/sitemap.xml', text)
        self.assertIn('Disallow: /admin/', text)
        disallowed = [l.split(': ')[1] for l in text.splitlines() if l.startswith('Disallow')]
        for public in ('/zabantu/', '/media/', '/static/'):
            self.assertFalse(any(public.startswith(d) for d in disallowed), public)

    def test_list_pages_have_their_own_share_title(self):
        html = self.client.get(reverse('public_article_list')).content.decode()
        self.assertIn('property="og:title" content="Publications - Zabantu"', html)
        self.assertIn('rel="canonical" href="https://zabantu.net/zabantu/publications/"', html)
        self.assertIn('property="og:title" content="Zabantu - Groupe de recherche',
                      self.client.get(reverse('home')).content.decode())
