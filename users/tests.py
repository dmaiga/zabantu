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


class BackofficeAccessTests(TestCase):
    PASSWORD = 'secret-pass-123'

    def login(self, user):
        return self.client.post(reverse('login'), {'username': user.username, 'password': self.PASSWORD})

    def test_member_cannot_log_in_by_default(self):
        from users.testing import make_user
        member = make_user('membre', backoffice_access=False)
        r = self.login(member)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'pas accès')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_wrong_password_still_says_invalid_credentials(self):
        from users.testing import make_user
        member = make_user('membre', backoffice_access=False)
        r = self.client.post(reverse('login'), {'username': member.username, 'password': 'faux'})
        self.assertContains(r, 'Identifiants invalides')

    def test_allowed_member_moderator_and_admin_can_log_in(self):
        from users.testing import make_user
        for role, flag in (('membre', True), ('moderateur', False), ('admin', False)):
            self.client.logout()
            user = make_user(role, backoffice_access=flag)
            self.assertRedirects(self.login(user), reverse('dashboard'), fetch_redirect_response=False, msg_prefix=role)

    def test_removing_access_cuts_the_open_session(self):
        from users.testing import make_user
        member = make_user('membre')
        self.login(member)
        self.assertEqual(self.client.get(reverse('dashboard')).status_code, 200)
        member.backoffice_access = False
        member.save()
        r = self.client.get(reverse('dashboard'))
        self.assertEqual(r.status_code, 302)
        self.assertIn('/auth/', r.url)

    def test_creating_a_member_defaults_to_no_access_and_sends_no_email(self):
        from users.testing import make_user
        self.client.force_login(make_user('moderateur'))
        data = {'email': 'nouveau@test.org', 'nom': 'Doe', 'prenom': 'Jane'}
        self.client.post(reverse('create_member'), data)
        member = get_user_model().objects.get(email='nouveau@test.org')
        self.assertFalse(member.backoffice_access)
        self.assertEqual(mail.outbox, [])

    def test_granting_access_at_creation_emails_a_password_link_that_works(self):
        from users.testing import make_user
        self.client.force_login(make_user('moderateur'))
        self.client.post(reverse('create_member'), {
            'email': 'acces@test.org', 'nom': 'Doe', 'prenom': 'Jane', 'backoffice_access': 'on'})
        self.assertEqual([m.to for m in mail.outbox], [['acces@test.org']])
        html = mail.outbox[0].alternatives[0][0]
        link = html.split('/password-reset-confirm/')[1].split('"')[0]
        r = self.client.get('/password-reset-confirm/' + link, follow=True)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'password')

    def test_moderator_can_grant_then_revoke_access_on_an_existing_member(self):
        from users.testing import make_user
        member = make_user('membre', backoffice_access=False)
        self.client.force_login(make_user('moderateur'))
        url = reverse('update_user', args=[member.pk])
        base = {'nom': 'Test', 'prenom': 'Membre', 'email': member.email}
        self.client.post(url, {**base, 'backoffice_access': 'on'})
        member.refresh_from_db()
        self.assertTrue(member.backoffice_access)
        self.client.post(url, base)
        member.refresh_from_db()
        self.assertFalse(member.backoffice_access)

    def test_member_cannot_edit_someone_else_or_grant_access(self):
        from users.testing import make_user
        other = make_user('membre', backoffice_access=False)
        me = make_user('membre')
        self.client.force_login(me)
        self.assertEqual(self.client.get(reverse('update_user', args=[other.pk])).status_code, 403)
        r = self.client.get(reverse('update_user', args=[me.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertNotIn('backoffice_access', r.context['form'].fields)

    def test_moderator_cannot_edit_an_admin(self):
        from users.testing import make_user
        admin = make_user('admin')
        self.client.force_login(make_user('moderateur'))
        self.assertEqual(self.client.get(reverse('update_user', args=[admin.pk])).status_code, 403)
