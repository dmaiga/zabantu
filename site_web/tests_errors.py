from django.core.exceptions import PermissionDenied
from django.test import Client, TestCase, override_settings
from django.urls import include, path
from django.views.defaults import bad_request


def boom(request):
    raise RuntimeError('panne de test')


def forbidden(request):
    raise PermissionDenied


def bad(request):
    return bad_request(request, Exception('x'))


urlpatterns = [
    path('boom/', boom),
    path('interdit/', forbidden),
    path('mauvaise/', bad),
    path('', include('zabantu.urls')),     # les vraies routes : les pages d'erreur y renvoient (accueil, contact…)
]


class ErrorPagesOnPublicSiteTests(TestCase):
    def test_404_uses_the_site_layout_and_links_home(self):
        r = self.client.get('/zabantu/cette-page-nexiste-pas/')
        self.assertEqual(r.status_code, 404)
        self.assertContains(r, "Cette page n'existe pas", status_code=404)
        self.assertContains(r, 'href="/zabantu/publications/"', status_code=404)
        self.assertContains(r, 'Mentions légales', status_code=404)        # pied de page du site


@override_settings(ROOT_URLCONF='site_web.tests_errors')
class StandaloneAndPermissionPagesTests(TestCase):
    def test_500_is_a_friendly_standalone_page(self):
        r = Client(raise_request_exception=False).get('/boom/')
        self.assertEqual(r.status_code, 500)
        html = r.content.decode()
        self.assertIn('Une erreur est survenue de notre côté', html)
        self.assertIn('Info@zabantu.net', html)
        self.assertNotIn('RuntimeError', html)                              # aucun détail technique
        self.assertNotIn('panne de test', html)

    def test_403_and_400_pages(self):
        self.assertContains(self.client.get('/interdit/'), 'autorisation', status_code=403)
        self.assertContains(self.client.get('/mauvaise/'), 'Requête invalide', status_code=400)

    def test_csrf_failure_explains_what_to_do(self):
        c = Client(enforce_csrf_checks=True)
        r = c.post('/zabantu/contact/', {'email': 'x@y.org'})
        self.assertContains(r, 'La page est restée ouverte trop longtemps', status_code=403)
