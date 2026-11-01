from django.test import TestCase
from django.urls import reverse


class LegalPagesTests(TestCase):
    def test_pages_are_public_and_cover_the_apdp_items(self):
        expected = {
            'legal_notice': ['Éditeur', 'Directeur de la publication', 'Hébergeur'],
            'privacy': ['Données collectées et finalités', 'Destinataires', 'Conservation', 'Vos droits', 'APDP'],
            'cookies': ['csrftoken', 'sessionid', 'Gérer ou refuser'],
        }
        for name, needles in expected.items():
            resp = self.client.get(reverse(name))
            self.assertEqual(resp.status_code, 200, name)
            html = resp.content.decode()
            for needle in needles:
                self.assertIn(needle, html, f'{name}: {needle}')

    def test_footer_links_to_the_legal_pages(self):
        html = self.client.get(reverse('home')).content.decode()
        for name in ('legal_notice', 'privacy', 'cookies'):
            self.assertIn(reverse(name), html)


class CookieBannerTests(TestCase):
    def test_banner_offers_accept_refuse_and_customize_on_public_pages(self):
        for name in ('home', 'privacy', 'contact'):
            html = self.client.get(reverse(name)).content.decode()
            for needle in ('id="cookie-banner"', 'data-cookie="accept"', 'data-cookie="refuse"',
                           'data-cookie="customize"', 'data-open-cookie-settings'):
                self.assertIn(needle, html, f'{name}: {needle}')

    def test_cookie_policy_lists_the_consent_cookie(self):
        self.assertContains(self.client.get(reverse('cookies')), 'zabantu_consent')
