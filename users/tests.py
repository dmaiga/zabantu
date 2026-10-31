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


class SuperuserAccessTests(TestCase):
    def test_createsuperuser_account_can_log_in_and_moderate(self):
        from django.core.management import call_command
        call_command('createsuperuser', interactive=False, username='root', email='root@test.org',
                     nom='Root', prenom='Super', verbosity=0)
        root = get_user_model().objects.get(username='root')
        root.set_password('secret-pass-123')
        root.save()
        self.assertEqual(root.role, 'admin')
        self.assertTrue(root.can_access_backoffice and root.can_moderate)
        r = self.client.post(reverse('login'), {'username': 'root', 'password': 'secret-pass-123'})
        self.assertRedirects(r, reverse('dashboard'), fetch_redirect_response=False)

    def test_superuser_keeps_access_even_if_role_was_changed_in_bulk(self):
        get_user_model().objects.create_superuser(
            username='su', email='su@test.org', password='x', nom='S', prenom='U')
        get_user_model().objects.filter(username='su').update(role='membre')
        su = get_user_model().objects.get(username='su')
        self.assertTrue(su.can_access_backoffice and su.can_moderate)


class ManagementScreensAccessTests(TestCase):
    """Les écrans de gestion (membres, messages, info-lettre, adhésions, partenaires) sont réservés aux modérateurs."""
    NAMES = ['user_list', 'create_member', 'newsletter_list', 'newsletter_campaign_list',
             'contact_message_list', 'sent_messages_list', 'membership_application_list', 'partenaire_list']

    def test_anonymous_is_sent_to_login(self):
        for name in self.NAMES:
            r = self.client.get(reverse(name))
            self.assertEqual(r.status_code, 302, name)
            self.assertIn('/auth/', r.url, name)

    def test_member_with_access_is_refused(self):
        from users.testing import make_user
        other = make_user('membre')
        self.client.force_login(make_user('membre'))
        for name in self.NAMES:
            self.assertEqual(self.client.get(reverse(name)).status_code, 403, name)
        self.assertEqual(self.client.get(reverse('user_detail', args=[other.pk])).status_code, 403)
        self.assertEqual(self.client.post(reverse('user_delete', args=[other.pk]), {'confirmation': 'SUPPRIMER'}).status_code, 403)
        self.assertTrue(get_user_model().objects.filter(pk=other.pk).exists())

    def test_moderator_can_open_them(self):
        from users.testing import make_user
        self.client.force_login(make_user('moderateur'))
        for name in self.NAMES:
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)


class MemberListTests(TestCase):
    def setUp(self):
        from users.testing import make_user
        self.client.force_login(make_user('moderateur'))
        for i in range(24):
            make_user('membre', backoffice_access=(i % 4 == 0), prenom=f'Prenom{i:02d}')

    def test_list_is_called_members_paginated_and_shows_names_in_normal_case(self):
        r = self.client.get(reverse('user_list'))
        self.assertContains(r, '<h1 class="h3 mb-0">Membres</h1>', html=True)
        self.assertEqual(len(r.context['page_obj']), 20)
        self.assertContains(r, 'Test</a>')  # « TEST » est stocké en majuscules, affiché en casse normale
        self.assertNotContains(r, 'TEST</a>')

    def test_access_filter(self):
        yes = self.client.get(reverse('user_list'), {'access': 'yes'}).context['page_obj']
        self.assertTrue(all(m.can_access_backoffice for m in yes))
        no = self.client.get(reverse('user_list'), {'access': 'no'}).context['page_obj']
        self.assertTrue(no and not any(m.can_access_backoffice for m in no))

    def test_search_by_name_and_invalid_role_ignored(self):
        r = self.client.get(reverse('user_list'), {'q': 'Prenom07', 'role': 'nope'})
        self.assertEqual(r.context['page_obj'].paginator.count, 1)

    def test_list_has_no_delete_action(self):
        r = self.client.get(reverse('user_list'))
        self.assertNotContains(r, '/users/delete/')


class PartenaireCrudTests(TestCase):
    def setUp(self):
        from users.models import Partenaire
        from users.testing import make_user
        self.p = Partenaire.objects.create(name='Fondation X', logo='partenaires/x.png', order=2)
        self.moderator = make_user('moderateur')

    def test_moderator_edits_a_partner(self):
        self.client.force_login(self.moderator)
        r = self.client.post(reverse('partenaire_update', args=[self.p.pk]), {'name': 'Fondation Y', 'order': 5, 'is_active': 'on'})
        self.assertRedirects(r, reverse('partenaire_list'))
        self.p.refresh_from_db()
        self.assertEqual((self.p.name, self.p.order), ('Fondation Y', 5))

    def test_delete_needs_post_and_a_moderator(self):
        from users.models import Partenaire
        from users.testing import make_user
        url = reverse('partenaire_delete', args=[self.p.pk])
        self.client.force_login(make_user('membre'))
        self.assertEqual(self.client.post(url).status_code, 403)
        self.client.force_login(self.moderator)
        self.assertEqual(self.client.get(url).status_code, 405)
        self.client.post(url)
        self.assertFalse(Partenaire.objects.filter(pk=self.p.pk).exists())

    def test_list_searches_by_name(self):
        from users.models import Partenaire
        Partenaire.objects.create(name='Autre', logo='partenaires/y.png')
        self.client.force_login(self.moderator)
        r = self.client.get(reverse('partenaire_list'), {'q': 'Fondation'})
        self.assertEqual([p.name for p in r.context['page_obj']], ['Fondation X'])


class SidebarOrderTests(TestCase):
    def test_intervenants_come_before_partenaires_for_moderators(self):
        from users.testing import make_user
        self.client.force_login(make_user('moderateur'))
        html = self.client.get(reverse('dashboard')).content.decode()
        self.assertLess(html.index('fa-chalkboard-teacher'), html.index('fa-handshake'))

    def test_members_still_see_intervenants_but_not_partenaires(self):
        from users.testing import make_user
        self.client.force_login(make_user('membre'))
        html = self.client.get(reverse('dashboard')).content.decode()
        self.assertIn('fa-chalkboard-teacher', html)
        self.assertNotIn('fa-handshake', html)
