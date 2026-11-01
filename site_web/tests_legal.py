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
    def test_banner_is_an_information_notice_without_optional_categories(self):
        for name in ('home', 'privacy', 'contact'):
            html = self.client.get(reverse(name)).content.decode()
            for needle in ('id="cookie-banner"', 'data-cookie="ack"', 'data-open-cookie-settings'):
                self.assertIn(needle, html, f'{name}: {needle}')
            self.assertNotIn('cookie-analytics', html, name)

    def test_cookie_policy_lists_the_notice_cookie_and_no_audience_tracking(self):
        html = self.client.get(reverse('cookies')).content.decode()
        self.assertIn('zabantu_consent', html)
        self.assertNotIn('si le site en utilise un jour', html)

    def test_banner_script_is_not_cut_short_by_a_closing_tag(self):
        # un « </script> » écrit dans le JavaScript (même en commentaire) ferait afficher le reste du code comme du texte
        html = self.client.get(reverse('home')).content.decode()
        start = html.index("var NAME = 'zabantu_consent'")
        self.assertIn('})();', html[start:html.index('</script>', start)])
