import datetime
from io import StringIO

from django.conf import settings
from django.contrib import admin
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from articles.models import Article
from site_web import views
from site_web.models import NewsletterSubscriber
from users.testing import make_user


def book(**kw):
    defaults = dict(title='Penser l\'État', article_type='ouvrage', status='published', content='<p>x</p>',
                    publisher_book='Éditions du Sahel', publication_place='Bamako', page_count=312,
                    publication_date=datetime.date(2025, 6, 15), academic_authors='Collectif')
    defaults.update(kw)
    return Article.objects.create(**defaults)


class PublicOuvrageTests(TestCase):
    def test_detail_page_shows_the_book_information(self):
        b = book()
        html = self.client.get(reverse('public_article_detail', args=[b.slug])).content.decode()
        for expected in ('Maison d’édition', 'Éditions du Sahel', 'Lieu de publication', 'Bamako',
                         'Nombre de pages', '312', 'Date de publication', '15 juin 2025'):
            self.assertIn(expected, html, expected)

    def test_other_types_do_not_show_book_fields(self):
        article = Article.objects.create(title='Revue', article_type='academic', status='published', content='x',
                                         journal='Revue X')
        self.assertNotIn('Maison d’édition', self.client.get(reverse('public_article_detail', args=[article.slug])).content.decode())

    def test_list_shows_publisher_date_and_a_type_badge(self):
        book()
        html = self.client.get(reverse('public_article_list'), {'type': 'ouvrage'}).content.decode()
        self.assertIn('Éditions du Sahel', html)
        self.assertIn('15 juin 2025', html)
        self.assertIn('>Ouvrage<', html)


class PublicCategoriesTests(TestCase):
    def test_categories_follow_the_production(self):
        self.assertNotIn('zabantu', views.CATEGORY_LABELS)
        self.assertEqual(views.CATEGORY_LABELS['academic'], 'Articles')
        self.assertEqual(list(views.CATEGORY_LABELS),
                         ['analyse', 'academic', 'ouvrage', 'policy', 'rapport', 'working', 'independent'])

    def test_public_menu_is_flat_like_production(self):
        html = self.client.get(reverse('home')).content.decode()
        for value in ('analyse', 'academic', 'ouvrage', 'policy', 'independent', 'rapport', 'working'):
            self.assertIn(f'?type={value}"', html, value)
        self.assertNotIn('?type=zabantu"', html)
        self.assertIn('zabantu_logo.jpg', html)  # icône du site


class ProductionToolingTests(TestCase):
    def test_subscribers_are_manageable_in_the_admin(self):
        self.assertIn(NewsletterSubscriber, admin.site._registry)

    def test_seed_newsletter_subscribes_active_accounts_without_duplicates(self):
        a = make_user('membre'); b = make_user('membre', is_active=False)
        NewsletterSubscriber.objects.create(email=a.email)
        c = make_user('moderateur')
        out = StringIO()
        call_command('seed_newsletter', stdout=out)
        emails = set(NewsletterSubscriber.objects.values_list('email', flat=True))
        self.assertIn(c.email, emails)
        self.assertNotIn(b.email, emails)  # compte inactif : ignoré
        self.assertEqual(NewsletterSubscriber.objects.filter(email=a.email).count(), 1)
        call_command('seed_newsletter', stdout=StringIO())  # relancé : rien de plus
        self.assertEqual(NewsletterSubscriber.objects.count(), len(emails))

    def test_static_files_are_served_by_whitenoise_like_in_production(self):
        self.assertIn('whitenoise.middleware.WhiteNoiseMiddleware', settings.MIDDLEWARE)
        self.assertLess(settings.MIDDLEWARE.index('django.middleware.security.SecurityMiddleware'),
                        settings.MIDDLEWARE.index('whitenoise.middleware.WhiteNoiseMiddleware'))
        self.assertIn('staticfiles', settings.STORAGES)


class MemberCardsLayoutTests(TestCase):
    """Un résumé de biographie coupé au milieu du HTML ne doit pas casser la grille des membres."""

    def make_members(self, n=7):
        from django.contrib.auth import get_user_model
        U = get_user_model()
        # biographie riche, assez longue pour être coupée, avec des balises ouvertes au moment de la coupure
        bio = '<div><p>' + ' '.join(f'mot{i}' for i in range(60)) + '</p><span><em>fin</em></span></div>'
        for i in range(n):
            U.objects.create_user(username=f'm{i}', email=f'm{i}@t.org', password='x', nom=f'Nom{i}', prenom='P',
                                  role='membre', bio=bio)

    def test_every_member_gets_its_own_column(self):
        self.make_members(7)
        html = self.client.get(reverse('public_member_list')).content.decode()
        self.assertEqual(html.count('class="card member-card'), 7)
        self.assertEqual(html.count('class="col-sm-6 col-md-4 col-xl-3 mb-4 d-flex align-items-stretch"'), 7)

    def test_each_card_shows_the_member_name(self):
        self.make_members(3)
        html = self.client.get(reverse('public_member_list')).content.decode()
        for i in range(3):
            self.assertIn(f'<h5 class="card-title">P NOM{i}</h5>', html)

    def test_the_card_shows_a_plain_text_excerpt(self):
        self.make_members(1)
        html = self.client.get(reverse('public_member_list')).content.decode()
        card = html.split('class="card-text">')[1].split('</p>')[0]
        self.assertNotIn('<', card)
        self.assertIn('mot0', card)
        self.assertNotIn('mot59', card)  # tronquée

    def test_balanced_markup_inside_the_grid(self):
        from html.parser import HTMLParser

        class Depth(HTMLParser):
            def __init__(self):
                super().__init__(); self.stack = []; self.problems = []
            def handle_starttag(self, tag, attrs):
                if tag not in ('img', 'br', 'hr', 'input', 'meta', 'link'): self.stack.append(tag)
            def handle_endtag(self, tag):
                if self.stack and self.stack[-1] == tag: self.stack.pop()
                else: self.problems.append(tag)
        self.make_members(4)
        html = self.client.get(reverse('public_member_list')).content.decode()
        grid = html.split('<div class="container py-5">')[1].split('</main>')[0]
        parser = Depth(); parser.feed('<div>' + grid)
        self.assertEqual(parser.problems, [])
