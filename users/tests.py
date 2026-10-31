from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class LoginPageTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='admin1', password='secret-pass-123', email='a@x.org', nom='A', prenom='B', role='admin')

    def test_page_has_enrolment_door_and_forgot_link(self):
        r = self.client.get(reverse('login'))
        self.assertContains(r, reverse('membership_apply'))
        self.assertContains(r, reverse('password_reset'))
        self.assertContains(r, 'Faire une demande d')

    def test_wrong_password_shows_an_error(self):
        r = self.client.post(reverse('login'), {'username': 'admin1', 'password': 'faux'})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Identifiants invalides')

    def test_login_redirects_to_dashboard(self):
        r = self.client.post(reverse('login'), {'username': 'admin1', 'password': 'secret-pass-123'})
        self.assertRedirects(r, reverse('dashboard'), fetch_redirect_response=False)

    def test_safe_next_is_followed(self):
        r = self.client.post(reverse('login') + '?next=/users/adhesions/',
                             {'username': 'admin1', 'password': 'secret-pass-123'})
        self.assertRedirects(r, '/users/adhesions/', fetch_redirect_response=False)

    def test_external_next_is_ignored(self):
        for target in ('https://exemple.com/piege', '//exemple.com', 'javascript:alert(1)'):
            self.client.logout()
            r = self.client.post(reverse('login') + '?next=' + target,
                                 {'username': 'admin1', 'password': 'secret-pass-123'})
            self.assertRedirects(r, reverse('dashboard'), fetch_redirect_response=False, msg_prefix=target)


from django.core import mail


class PasswordResetFlowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='adm', password='secret-pass-123', email='adm@x.org', nom='A', prenom='B', role='admin')

    def test_pages_share_the_login_layout(self):
        for name in ('password_reset', 'password_reset_done', 'password_reset_complete'):
            r = self.client.get(reverse(name))
            self.assertEqual(r.status_code, 200, name)
            self.assertContains(r, 'login-wrapper', msg_prefix=name)
            self.assertContains(r, 'brand-section', msg_prefix=name)

    def test_done_page_does_not_claim_password_was_changed(self):
        r = self.client.get(reverse('password_reset_done'))
        self.assertContains(r, 'Vérifiez votre boîte mail')
        self.assertNotContains(r, 'modifié avec succès')
        self.assertNotContains(r, 'a été changé')

    def test_complete_page_confirms_change(self):
        self.assertContains(self.client.get(reverse('password_reset_complete')), 'Mot de passe modifié')

    def test_email_is_text_with_html_alternative(self):
        r = self.client.post(reverse('password_reset'), {'email': 'adm@x.org'})
        self.assertRedirects(r, reverse('password_reset_done'), fetch_redirect_response=False)
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertNotIn('<html', message.body.lower())          # corps texte propre, pas du HTML brut
        self.assertIn('/password-reset-confirm/', message.body)
        self.assertEqual(len(message.alternatives), 1)
        self.assertIn('text/html', message.alternatives[0][1])
        self.assertIn('Réinitialisation', message.subject)

    def test_unknown_email_gets_same_response_and_no_mail(self):
        r = self.client.post(reverse('password_reset'), {'email': 'inconnu@x.org'})
        self.assertRedirects(r, reverse('password_reset_done'), fetch_redirect_response=False)
        self.assertEqual(len(mail.outbox), 0)

    def test_confirm_flow_and_errors_displayed(self):
        self.client.post(reverse('password_reset'), {'email': 'adm@x.org'})
        link = [l for l in mail.outbox[0].body.split() if '/password-reset-confirm/' in l][0]
        path = link.split('://', 1)[1].split('/', 1)[1]
        r = self.client.get('/' + path, follow=True)
        self.assertContains(r, 'Nouveau mot de passe')
        form_url = r.redirect_chain[-1][0] if r.redirect_chain else '/' + path
        r = self.client.post(form_url, {'new_password1': 'abc', 'new_password2': 'different'})
        self.assertContains(r, 'error-alert')
        r = self.client.post(form_url, {'new_password1': 'Un-mot-de-passe-solide-42', 'new_password2': 'Un-mot-de-passe-solide-42'})
        self.assertRedirects(r, reverse('password_reset_complete'), fetch_redirect_response=False)
        self.assertTrue(get_user_model().objects.get(pk=self.user.pk).check_password('Un-mot-de-passe-solide-42'))

    def test_invalid_link_page(self):
        r = self.client.get(reverse('password_reset_confirm', args=['abc', 'token-invalide']))
        self.assertContains(r, 'Lien invalide')


class PartenaireBackofficeTests(TestCase):
    def setUp(self):
        from users.models import Partenaire
        from users.testing import make_user
        self.partenaire = Partenaire.objects.create(name='Fondation X', logo='partenaires/x.png')
        self.member = make_user('membre')
        self.moderator = make_user('moderateur')

    def test_member_cannot_see_or_toggle_partners(self):
        self.client.force_login(self.member)
        self.assertEqual(self.client.get(reverse('partenaire_list')).status_code, 403)
        self.assertEqual(self.client.post(reverse('partenaire_toggle', args=[self.partenaire.pk])).status_code, 403)

    def test_toggle_requires_post_and_flips_status(self):
        self.client.force_login(self.moderator)
        url = reverse('partenaire_toggle', args=[self.partenaire.pk])
        self.assertEqual(self.client.get(url).status_code, 405)
        self.client.post(url)
        self.partenaire.refresh_from_db()
        self.assertFalse(self.partenaire.is_active)
