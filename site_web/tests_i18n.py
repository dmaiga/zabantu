"""Lot 4 : site bilingue français / anglais (zabantu/i18n.py).

Français aux adresses actuelles, anglais sous /en/ ; textes fixes traduits (locale/en), contenus avec champs « _en »
facultatifs et repli sur le français ; backoffice toujours en français ; e-mails dans la langue du destinataire.
"""
from datetime import timedelta

from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone, translation

from articles.models import Article, Guelekan
from events.models import Event
from users.testing import make_user
from zabantu.i18n import is_blank, translated

from . import mailing
from .models import ContactMessage, MembershipApplication, NewsletterSubscriber
from .tests import _MEDIA, VALID, _png
from .tests_helpers import human


def en(name, *args):
    with translation.override('en'):
        return reverse(name, args=args)


def publish(title, **kw):
    kw.setdefault('content', '<p>Contenu français</p>')
    return Article.objects.create(title=title, status='published', publish_at=timezone.now(), **kw)


class AddressesAndLanguageTests(TestCase):
    def test_french_addresses_are_unchanged_and_english_ones_are_prefixed(self):
        self.assertEqual(reverse('contact'), '/zabantu/contact/')
        self.assertEqual(en('contact'), '/en/zabantu/contact/')
        self.assertEqual(en('home'), '/en/zabantu/')

    def test_language_comes_from_the_address_only(self):
        r = self.client.get('/zabantu/', HTTP_ACCEPT_LANGUAGE='en')   # navigateur anglais, adresse française
        self.assertContains(r, '<html lang="fr">')
        self.assertContains(r, 'Faire un don')
        self.assertEqual(r['Content-Language'], 'fr')
        r = self.client.get('/en/zabantu/')
        self.assertContains(r, '<html lang="en">')
        self.assertContains(r, 'Donate</a>')
        self.assertNotContains(r, 'Faire un don</a>')
        self.assertEqual(r['Content-Language'], 'en')

    def test_backoffice_stays_in_french_for_an_english_browser(self):
        self.client.force_login(make_user('admin'))
        r = self.client.get(reverse('event_create'), HTTP_ACCEPT_LANGUAGE='en')
        self.assertContains(r, 'Version anglaise (facultatif)')
        self.assertContains(r, 'Champ obligatoire')
        self.assertEqual(self.client.get('/en/users/dashboard/').status_code, 404)   # pas de backoffice anglais

    def test_language_does_not_leak_to_the_next_request_or_to_code_outside_requests(self):
        self.client.get('/en/zabantu/')
        self.assertEqual(translation.get_language(), 'fr')
        self.assertEqual(reverse('home'), '/zabantu/')

    def test_switcher_and_hreflang_point_to_the_same_page_in_the_other_language(self):
        r = self.client.get('/zabantu/publications/?type=rapport&q=mali&sort=title_asc')
        self.assertContains(r, 'href="/en/zabantu/publications/?type=rapport&amp;q=mali&amp;sort=title_asc" class="lang-link',
                            count=2)                                       # sélecteur : mobile + bureau, recherche gardée
        # hreflang : filtre gardé, recherche et tri retirés
        self.assertContains(r, 'hreflang="fr" href="http://testserver/zabantu/publications/?type=rapport"')
        self.assertContains(r, 'hreflang="en" href="http://testserver/en/zabantu/publications/?type=rapport"')
        self.assertContains(r, 'hreflang="x-default" href="http://testserver/zabantu/publications/?type=rapport"')
        self.assertContains(r, '<meta property="og:locale" content="fr_FR">')
        r = self.client.get('/en/zabantu/publications/')
        self.assertContains(r, 'href="/zabantu/publications/" class="lang-link', count=2)
        self.assertContains(r, '<meta property="og:locale" content="en_GB">')

    def test_english_404_page(self):
        r = self.client.get('/en/zabantu/nope/')
        self.assertContains(r, 'Page not found', status_code=404)
        self.assertNotContains(r, 'class="lang-link', status_code=404)   # page sans équivalent : pas de sélecteur

    def test_every_public_page_answers_in_english(self):
        pages = ['home', 'public_article_list', 'public_event_list', 'public_member_list', 'about', 'contact', 'donate',
                 'membership_apply', 'membership_thanks', 'liste_galeries', 'toutes_photos', 'legal_notice', 'privacy',
                 'cookies']
        for name in pages:
            with self.subTest(name):
                r = self.client.get(en(name))
                self.assertEqual(r.status_code, 200)
                self.assertContains(r, '<html lang="en">')
                self.assertContains(r, 'Legal notice')        # pied de page traduit


@override_settings(MEDIA_ROOT=_MEDIA)   # vraies images d'événements : les miniatures se créent sans erreur
class FixedTextTests(TestCase):
    def test_messages_forms_and_choices_are_translated(self):
        r = self.client.get(en('membership_apply'))
        for text in ('Zabantu membership form', 'Full name', 'PhD candidate', 'A colleague or a friend', 'Send my application'):
            self.assertContains(r, text)
        r = self.client.post(en('newsletter_subscribe'), human({'email': 'reader@example.org'}), follow=True)
        self.assertContains(r, 'You are now subscribed to our newsletter!')
        self.assertEqual(r.redirect_chain[-1][0], '/en/zabantu/')     # retour à l'accueil anglais

    def test_antispam_message_in_english(self):
        r = self.client.post(en('contact'), {**human(VALID), 'company_site': 'robot'})
        self.assertContains(r, 'Submission refused')

    def test_dates_are_written_in_english(self):
        march = timezone.now().replace(year=timezone.now().year + 1, month=3, day=12)
        event = Event.objects.create(title='Conférence', content='x', image=_png(), status='published',
                                     date=march, event_type='conference')
        self.assertContains(self.client.get(en('public_event_detail', event.pk)), f'12 March {march.year}')
        self.assertContains(self.client.get(reverse('public_event_detail', args=[event.pk])), f'12 mars {march.year}')

    def test_legal_pages_have_an_english_version_and_say_the_french_one_prevails(self):
        r = self.client.get(en('privacy'))
        self.assertContains(r, 'Privacy policy')
        self.assertContains(r, 'the <a href="/zabantu/confidentialite/" lang="fr" hreflang="fr">French version</a> prevails')
        self.assertNotContains(self.client.get(reverse('privacy')), 'French version')

    def test_compiled_catalogue_is_shipped(self):
        with translation.override('en'):
            self.assertEqual(translation.gettext('Faire un don'), 'Donate')
            self.assertEqual(translation.ngettext('%(n)s photo', '%(n)s photos', 2) % {'n': 2}, '2 photos')


@override_settings(MEDIA_ROOT=_MEDIA)
class ContentFallbackTests(TestCase):
    def test_english_field_is_used_when_filled_and_french_otherwise(self):
        article = publish('Titre français', title_en='English title', content_en='<p><br></p>')
        with translation.override('en'):
            self.assertEqual(article.t.title, 'English title')
            self.assertEqual(article.t.content, '<p>Contenu français</p>')       # anglais vide : repli
            self.assertEqual((article.t.lang_title, article.t.lang_content), ('en', 'fr'))
        self.assertEqual(article.t.title, 'Titre français')                     # page française

    def test_blank_rich_text(self):
        for value in (None, '', '  ', '<p><br></p>', '<p>&nbsp;</p>'):
            self.assertTrue(is_blank(value), value)
        for value in ('Texte', '<p><img src="x.png"></p>', 0):
            self.assertFalse(is_blank(value), value)

    def test_pages_show_english_content_or_mark_french_fallback(self):
        translated_article = publish('Titre français', title_en='English title', content_en='<p>English body</p>')
        french_only = publish('Seulement en français')
        r = self.client.get(en('public_article_detail', translated_article.slug))
        self.assertContains(r, '<h1 class="article-title" lang="en">English title</h1>', html=True)
        self.assertContains(r, 'English body')
        self.assertContains(r, '<meta property="og:title" content="English title">')
        r = self.client.get(en('public_article_detail', french_only.slug))
        self.assertContains(r, '<h1 class="article-title" lang="fr">Seulement en français</h1>', html=True)
        self.assertContains(self.client.get(reverse('public_article_detail', args=[translated_article.slug])),
                            'Titre français')

    def test_translation_rule_follows_the_main_content(self):
        self.assertFalse(publish('A', title_en='A').is_translated())                     # corps resté en français
        self.assertTrue(publish('B', title_en='B', content_en='<p>x</p>').is_translated())
        self.assertTrue(publish('C', title_en='C', content='', resume='<p>r</p>', resume_en='<p>s</p>').is_translated())
        self.assertFalse(publish('D', content_en='<p>x</p>').is_translated())           # titre manquant
        member = make_user('membre', bio='Biographie')
        self.assertFalse(member.is_translated())
        member.bio_en = 'Biography'
        self.assertTrue(member.is_translated())

    @override_settings(SEO_START_DATE=timezone.now().date() - timedelta(days=1))
    def test_untranslated_english_page_is_reachable_but_not_indexed(self):
        french_only = publish('Seulement en français')
        r = self.client.get(en('public_article_detail', french_only.slug))
        self.assertContains(r, '<meta name="robots" content="noindex,follow">')
        self.assertNotContains(r, 'rel="canonical"')
        self.assertNotContains(r, 'hreflang="en" href=')
        self.assertContains(r, 'class="lang-link')                             # le sélecteur reste utilisable
        r = self.client.get(reverse('public_article_detail', args=[french_only.slug]))
        self.assertNotContains(r, 'noindex')
        self.assertNotContains(r, 'hreflang="en" href=')                      # la page française n'annonce pas l'anglaise
        self.assertContains(r, 'rel="canonical"')

    @override_settings(SEO_START_DATE=timezone.now().date() - timedelta(days=1))
    def test_translated_english_page_is_indexed_with_its_own_canonical(self):
        article = publish('Titre', title_en='Title', content_en='<p>Body</p>')
        r = self.client.get(en('public_article_detail', article.slug))
        self.assertNotContains(r, 'noindex')
        self.assertContains(r, f'<link rel="canonical" href="http://testserver/en/zabantu/publications/{article.slug}/">')
        self.assertContains(r, f'hreflang="fr" href="http://testserver/zabantu/publications/{article.slug}/"')

    def test_list_search_finds_english_titles(self):
        publish('Racines agraires', title_en='Agrarian roots')
        r = self.client.get(en('public_article_list'), {'q': 'agrarian'})
        self.assertContains(r, 'Agrarian roots')

    def test_event_and_seminar_fallback(self):
        event = Event.objects.create(title='Atelier', title_en='Workshop on land', content='x', image=_png(),
                                     status='published', date=timezone.now() + timedelta(days=3))
        self.assertContains(self.client.get(en('public_event_detail', event.pk)), 'Workshop on land')
        gk = Guelekan.objects.create(title='Gɛlɛkan 1', content='<p>Compte rendu</p>', status='published')
        self.assertContains(self.client.get(en('public_guelekan_detail', gk.slug)), 'Compte rendu')


class BackofficeEnglishFieldsTests(TestCase):
    def setUp(self):
        self.client.force_login(make_user('moderateur'))

    def test_english_step_follows_the_french_fields_of_each_type(self):
        from articles.forms import AcademicForm, ArticleForm
        self.assertEqual([n for n in ArticleForm().fields if n.endswith('_en')], ['title_en', 'subtitle_en', 'content_en'])
        self.assertEqual([n for n in AcademicForm().fields if n.endswith('_en')], ['title_en', 'abstract_en'])
        form = ArticleForm()
        self.assertFalse(form.fields['content_en'].required)
        self.assertIs(type(form.fields['content_en'].widget), type(form.fields['content'].widget))  # même éditeur riche

    def test_ouvrage_saved_with_its_english_version(self):
        data = {'title': "Penser l'État", 'subtitle': 'Essai', 'academic_authors': 'Collectif',
                'publisher_book': 'Éditions du Sahel', 'publication_date': '2025-06-15', 'resume': '<p>Résumé</p>',
                'title_en': 'Thinking the State', 'resume_en': '<p>Abstract</p>', 'article_type': 'ouvrage'}
        self.client.post(reverse('article_create') + '?type=ouvrage', data)
        book = Article.objects.get(title="Penser l'État")
        self.assertEqual((book.title_en, book.resume_en, book.subtitle_en or ''), ('Thinking the State', '<p>Abstract</p>', ''))


class EmailLanguageTests(TestCase):
    def test_application_from_the_english_site_gets_english_emails(self):
        self.client.post(en('membership_apply'), human(VALID))
        application = MembershipApplication.objects.get()
        self.assertEqual(application.language, 'en')
        self.assertEqual(mail.outbox[-1].subject, 'Your application to join Zabantu')
        self.assertIn('Hello Awa Traoré,', mail.outbox[-1].alternatives[0][0])
        mailing.send_application_approved(application)
        self.assertEqual(mail.outbox[-1].subject, 'Welcome to Zabantu: your membership has been approved')
        self.assertIn('http://testserver/en/zabantu/membres/', mail.outbox[-1].alternatives[0][0])

    def test_french_application_stays_french(self):
        self.client.post(reverse('membership_apply'), human(VALID))
        self.assertEqual(MembershipApplication.objects.get().language, 'fr')
        self.assertEqual(mail.outbox[-1].subject, "Votre demande d'adhésion à Zabantu")

    def test_announcements_follow_each_subscriber_language(self):
        self.client.post(en('newsletter_subscribe'), human({'email': 'reader@example.org'}))
        self.client.post(reverse('newsletter_subscribe'), human({'email': 'lecteur@example.org'}))
        self.assertEqual(NewsletterSubscriber.objects.get(email='reader@example.org').language, 'en')
        article = publish('Titre français', title_en='English title', content_en='<p>English summary</p>')
        mailing.send_pending()
        by_address = {m.to[0]: m for m in mail.outbox}
        english, french = by_address['reader@example.org'], by_address['lecteur@example.org']
        self.assertEqual(english.subject, 'New publication: English title')
        self.assertIn(f'http://testserver/en/zabantu/publications/{article.slug}/', english.body)
        self.assertIn('Unsubscribe: http://testserver/en/zabantu/newsletter/unsubscribe/', english.body)
        self.assertIn('English summary', english.body)
        self.assertEqual(french.subject, 'Nouvelle publication : Titre français')
        self.assertIn(f'http://testserver/zabantu/publications/{article.slug}/', french.body)

    def test_resubscribing_from_the_other_site_switches_language(self):
        NewsletterSubscriber.objects.create(email='reader@example.org', language='fr')
        self.client.post(en('newsletter_subscribe'), human({'email': 'reader@example.org'}))
        self.assertEqual(NewsletterSubscriber.objects.get().language, 'en')

    def test_contact_reply_is_laid_out_in_the_message_language(self):
        self.client.post(en('contact'), human({'name': 'Doe', 'last_name': 'Jane', 'email': 'jane@example.org',
                                               'subject': 'information', 'message': 'Hello'}))
        message = ContactMessage.objects.get()
        self.assertEqual(message.language, 'en')
        self.client.force_login(make_user('moderateur'))
        self.assertContains(self.client.get(reverse('contact_message_detail', args=[message.pk])),
                            'Envoyé depuis le site en anglais')
        self.client.post(reverse('contact_message_reply', args=[message.pk]), {'reply_content': 'Thanks!'})
        self.assertIn('Thank you for your message. Here is our reply:', mail.outbox[-1].alternatives[0][0])


class SitemapAndCacheTests(TestCase):
    @override_settings(SEO_START_DATE=timezone.now().date() - timedelta(days=1))
    def test_sitemap_lists_english_only_for_translated_content(self):
        article = publish('Nouveau', title_en='New', content_en='<p>Body</p>')
        french_only = publish('Seulement en français')
        xml = self.client.get('/sitemap.xml').content.decode()
        fr_url = f'http://testserver/zabantu/publications/{article.slug}/'
        en_url = f'http://testserver/en/zabantu/publications/{article.slug}/'
        self.assertIn(f'<loc>{fr_url}</loc>', xml)
        self.assertIn(f'<loc>{en_url}</loc>', xml)
        self.assertEqual(xml.count(f'<xhtml:link href="{en_url}" hreflang="en" rel="alternate">'), 2)
        self.assertEqual(xml.count(f'<xhtml:link href="{fr_url}" hreflang="x-default" rel="alternate">'), 2)
        self.assertIn(f'<loc>http://testserver/zabantu/publications/{french_only.slug}/</loc>', xml)
        self.assertNotIn(f'/en/zabantu/publications/{french_only.slug}/', xml)

    @override_settings(PAGE_CACHE_TIMEOUT=600)
    def test_cached_fragments_are_kept_per_language(self):
        cache.clear()
        publish('Titre français', title_en='English title')
        self.assertContains(self.client.get(reverse('home')), 'Titre français')
        r = self.client.get(en('home'))
        self.assertContains(r, 'English title')
        self.assertContains(r, 'Latest publications')
        self.assertContains(self.client.get(reverse('home')), 'Dernières publications')
        self.assertContains(self.client.get(en('public_article_list')), 'English title')
        self.assertContains(self.client.get(reverse('public_article_list')), 'Titre français')


class CatalogueTests(TestCase):
    """Le .mo est versionné (msgfmt absent du serveur) : il doit correspondre au .po, sinon une traduction ajoutée
    au .po n'apparaîtrait jamais en production."""

    def _po_entries(self, path):
        import ast
        entries, current, key = [], {}, None
        for line in open(path, encoding='utf-8'):
            line = line.strip()
            if not line or line.startswith('#'):
                if current:
                    entries.append(current)
                current, key = {}, None
                continue
            if line.startswith('"'):
                current[key] += ast.literal_eval(line)
                continue
            key, _, value = line.partition(' ')
            current[key] = ast.literal_eval(value)
        if current:
            entries.append(current)
        return [e for e in entries if e.get('msgid')]

    def test_compiled_catalogue_matches_the_po_file(self):
        import gettext
        from django.conf import settings
        base = settings.BASE_DIR / 'locale' / 'en' / 'LC_MESSAGES'
        with open(base / 'django.mo', 'rb') as handle:
            catalogue = gettext.GNUTranslations(handle)
        missing = []
        for entry in self._po_entries(base / 'django.po'):
            if 'msgid_plural' in entry:
                if entry.get('msgstr[0]') and catalogue.ngettext(entry['msgid'], entry['msgid_plural'], 1) != entry['msgstr[0]']:
                    missing.append(entry['msgid'])
            elif entry.get('msgstr') and catalogue.gettext(entry['msgid']) != entry['msgstr']:
                missing.append(entry['msgid'])
        self.assertEqual(missing, [], "Relancer : python manage.py compilemessages -l en --ignore=.venv")
