"""Retours visuels du 2026-11-11 : sections vides masquées, liste des publications vide utile, boutons de partage,
mur de photos sans filtres, page de contact réorganisée (petite carte, FAQ, encadré de don)."""
from datetime import timedelta

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from articles.models import Article
from events.models import Event
from gallery.models import Photo, PhotoTag

from .tests import _MEDIA, _png


def publish(title, **kw):
    kw.setdefault('content', '<p>x</p>')
    return Article.objects.create(title=title, status='published', publish_at=timezone.now(), **kw)


@override_settings(MEDIA_ROOT=_MEDIA)
class EmptySectionsTests(TestCase):
    def test_home_hides_empty_sections(self):
        r = self.client.get(reverse('home'))
        self.assertNotContains(r, 'id="events"')
        self.assertNotContains(r, 'id="publications"')
        self.assertNotContains(r, 'class="stats-strip"')
        self.assertNotContains(r, 'Aucun événement prévu')

    def test_home_shows_sections_with_content(self):
        publish('Une analyse')
        Event.objects.create(title='Conférence', content='x', image=_png(), status='published', event_type='conference',
                             date=timezone.now() + timedelta(days=3))
        r = self.client.get(reverse('home'))
        self.assertContains(r, 'id="events"')
        self.assertContains(r, 'id="publications"')
        self.assertContains(r, 'class="stats-strip"')

    def test_about_hides_partners_and_team_when_empty(self):
        r = self.client.get(reverse('about'))
        self.assertNotContains(r, 'id="partenaires"')
        self.assertNotContains(r, 'id="equipe"')

    def test_event_list_hides_empty_parts(self):
        r = self.client.get(reverse('public_event_list'))
        self.assertNotContains(r, 'Événements à venir')
        self.assertNotContains(r, 'Événements passés')
        self.assertContains(r, 'Aucun événement pour le moment')
        Event.objects.create(title='Ancien', content='x', image=_png(), status='published', event_type='conference',
                             date=timezone.now() - timedelta(days=3))
        r = self.client.get(reverse('public_event_list'))
        self.assertContains(r, 'Événements passés')
        self.assertNotContains(r, 'Événements à venir')
        self.assertNotContains(r, 'Aucun événement pour le moment')


class EmptyPublicationListTests(TestCase):
    def test_empty_category_suggests_other_categories_and_recent_publications(self):
        publish('Rapport annuel', article_type='rapport')
        r = self.client.get(reverse('public_article_list'), {'type': 'working'})
        self.assertContains(r, 'Pas encore de publication dans « Working Papers »')
        self.assertContains(r, 'href="/zabantu/publications/?type=rapport"')        # catégorie qui a du contenu
        self.assertNotContains(r, 'href="/zabantu/publications/?type=ouvrage"><')    # catégorie vide non proposée
        self.assertContains(r, 'Publications récentes')
        self.assertContains(r, 'Rapport annuel')

    def test_search_without_result_offers_to_clear_it(self):
        publish('Rapport annuel', article_type='rapport')
        r = self.client.get(reverse('public_article_list'), {'type': 'rapport', 'q': 'introuvable'})
        self.assertContains(r, 'Aucun résultat pour « introuvable »')
        self.assertContains(r, 'href="/zabantu/publications/?type=rapport" class="btn btn-primary">Effacer la recherche')


class ShareButtonsTests(TestCase):
    def test_publication_has_share_links_with_the_page_address(self):
        article = publish('Racines agraires')
        r = self.client.get(reverse('public_article_detail', args=[article.slug]))
        address = f'http%3A%2F%2Ftestserver%2Fzabantu%2Fpublications%2F{article.slug}%2F'
        self.assertContains(r, f'https://www.facebook.com/sharer/sharer.php?u={address}', count=1)
        self.assertContains(r, f'https://www.linkedin.com/sharing/share-offsite/?url={address}', count=1)
        self.assertContains(r, 'https://wa.me/?text=Racines%20agraires%20' + address, count=1)
        self.assertContains(r, 'data-share-copy data-copied', count=1)
        self.assertContains(r, 'window.zabantuShareReady = true', count=1)                  # script chargé une fois
        self.assertNotContains(r, '{#')                                                     # aucun commentaire de gabarit affiché

    def test_english_page_shares_the_english_address(self):
        article = publish('Racines', title_en='Roots', content_en='<p>Body</p>')
        r = self.client.get(f'/en/zabantu/publications/{article.slug}/')
        self.assertContains(r, f'u=http%3A%2F%2Ftestserver%2Fen%2Fzabantu%2Fpublications%2F{article.slug}%2F')
        self.assertContains(r, 'Copy link')


@override_settings(MEDIA_ROOT=_MEDIA)
class PhotoWallTests(TestCase):
    def test_all_photos_is_a_masonry_wall_without_filter_bars(self):
        tag = PhotoTag.objects.create(name='Terrain', slug='terrain')
        photo = Photo.objects.create(title='Atelier', image=_png())
        photo.tags.add(tag)
        r = self.client.get(reverse('toutes_photos'))
        self.assertContains(r, 'class="photo-masonry pswp-gallery"')
        self.assertNotContains(r, 'Filtrer par galerie')
        self.assertNotContains(r, 'Filtrer par mot-clé')
        r = self.client.get(reverse('toutes_photos'), {'tag': 'terrain'})       # lien depuis les mots-clés d'une photo
        self.assertContains(r, 'Sélection : #Terrain')


class ContactLayoutTests(TestCase):
    def test_small_map_faq_and_donation_box(self):
        r = self.client.get(reverse('contact'))
        html = r.content.decode()
        self.assertContains(r, 'class="contact-map"')
        self.assertContains(r, 'https://www.google.com/maps/search/?api=1&amp;query=FSEG+Badalabougou+Bamako')
        self.assertContains(r, 'Comment soutenir Zabantu ?')
        self.assertContains(r, f'href="{reverse("contact")}?sujet=don#formulaire"')
        self.assertLess(html.index('class="contact-map"'), html.index('id="faqAccordion"'))   # carte dans la colonne


class TemplateCommentTests(TestCase):
    def test_no_multiline_hash_comment(self):
        """{# … #} ne vaut que sur une ligne : sur plusieurs, Django l'affiche tel quel dans la page.
        Utiliser {% comment %} … {% endcomment %}."""
        import re
        from pathlib import Path
        from django.conf import settings
        offenders = []
        for path in Path(settings.BASE_DIR).glob('*/templates/**/*.html'):
            text = path.read_text(encoding='utf-8')
            for match in re.finditer(r'\{#(.*?)#\}', text, re.S):
                if '\n' in match.group(1):
                    offenders.append(f'{path.relative_to(settings.BASE_DIR)}:{text[:match.start()].count(chr(10)) + 1}')
        self.assertEqual(offenders, [])


@override_settings(MEDIA_ROOT=_MEDIA)
class EventPagesTests(TestCase):
    def test_event_list_shows_the_last_six_gelekan_editions(self):
        for day in range(1, 9):
            Event.objects.create(title=f'Gɛlɛkan {day}', content='x', image=_png(), status='published',
                                 event_type='seminaire', date=timezone.now() - timedelta(days=day))
        self.assertContains(self.client.get(reverse('public_event_list')), 'class="gk-item past"', count=6)
        self.assertContains(self.client.get(reverse('public_event_list'), {'type': 'seminaire'}),
                            'class="gk-item past"', count=8)

    def test_event_detail_has_poster_practical_info_then_description(self):
        event = Event.objects.create(title='Webinaire', content='<p>Programme détaillé</p>', image=_png(),
                                     status='published', event_type='webinaire', is_webinar=True,
                                     webinar_link='https://meet.example/abc', date=timezone.now() + timedelta(days=2))
        r = self.client.get(reverse('public_event_detail', args=[event.pk]))
        html = r.content.decode()
        self.assertContains(r, 'Infos pratiques')
        self.assertContains(r, 'Rejoindre le webinaire', count=1)               # un seul bouton, dans les infos pratiques
        self.assertNotContains(r, 'event-cta')
        self.assertLess(html.index('class="event-poster"'), html.index('class="event-info-card"'))
        self.assertLess(html.index('class="event-info-card"'), html.index('class="event-content"'))


class PublicationCardAuthorsTests(TestCase):
    def test_external_authors_of_a_book_are_listed(self):
        publish('Un ouvrage', article_type='ouvrage', academic_authors='Modibo TRAORE')
        self.assertContains(self.client.get(reverse('public_article_list')), '<i class="fas fa-user"></i>Modibo TRAORE</p>')


class FooterTests(TestCase):
    def test_footer_guides_to_the_essentials_without_duplicates(self):
        import re
        html = self.client.get(reverse('about')).content.decode()
        footer = html[html.index('<footer class="zabantu-footer'):html.index('</footer>')]
        links = re.findall(r'href="([^"]+)"', footer)
        self.assertEqual(len(links), len(set(links)), links)                     # aucun lien en double
        for name in ('public_article_list', 'public_event_list', 'membership_apply', 'training_list', 'contact', 'privacy'):
            self.assertIn(reverse(name), links)
        self.assertNotIn(reverse('donate'), links)                               # le don est porté par le bandeau
