from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .forms import MembershipApplicationForm
from .models import MembershipApplication

VALID = {
    'full_name': 'Awa Traoré',
    'email': 'awa@example.org',
    'phone': '',
    'city_country': 'Bamako, Mali',
    'academic_status': 'doctorant',
    'institution': 'USSGB',
    'research_interests': 'Économie rurale',
    'how_heard_choices': ['collegue', 'site_web'],
    'how_heard': '',
    'contribution': 'Participer aux séminaires',
    'career_benefit': 'Réseau de recherche',
    'consent': 'on',
}


class MembershipFormTests(TestCase):
    def test_page_loads(self):
        self.assertEqual(self.client.get(reverse('membership_apply')).status_code, 200)

    def test_consent_required(self):
        data = {**VALID}
        data.pop('consent')
        form = MembershipApplicationForm(data)
        self.assertIn('consent', form.errors)

    def test_word_limit(self):
        form = MembershipApplicationForm({**VALID, 'contribution': 'mot ' * 101})
        self.assertIn('contribution', form.errors)
        form = MembershipApplicationForm({**VALID, 'contribution': 'mot ' * 100})
        self.assertNotIn('contribution', form.errors)


class MembershipWorkflowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='admin', password='x', email='a@b.c')
        data = {k: v for k, v in VALID.items() if k != 'consent'}
        self.app = MembershipApplication.objects.create(consent=True, **data)

    def test_default_pending(self):
        self.assertEqual(self.app.status, MembershipApplication.Status.PENDING)

    def test_approve_then_revoke(self):
        self.app.approve(self.user)
        self.assertEqual(self.app.status, 'approved')
        self.assertEqual(self.app.reviewed_by, self.user)
        self.app.revoke(self.user, 'Inactivité')
        self.assertEqual(self.app.status, 'revoked')
        self.assertEqual(self.app.revoked_by, self.user)
        self.assertEqual(self.app.revocation_reason, 'Inactivité')

    def test_cannot_revoke_pending(self):
        with self.assertRaises(ValueError):
            self.app.revoke(self.user)

    def test_admin_actions(self):
        self.user.is_staff = self.user.is_superuser = True
        self.user.save()
        self.client.force_login(self.user)
        url = reverse('admin:site_web_membershipapplication_changelist')
        self.assertEqual(self.client.get(url).status_code, 200)
        self.client.post(url, {'action': 'approve_applications', '_selected_action': [self.app.pk]})
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, 'approved')
        self.client.post(url, {'action': 'revoke_applications', '_selected_action': [self.app.pk]})
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, 'revoked')


class BackofficeApplicationTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(username='adm', password='x', email='adm@x.org',
                                              nom='A', prenom='B', role='admin')
        self.member = User.objects.create_user(username='mem', password='x', email='mem@x.org',
                                               nom='C', prenom='D', role='membre')
        data = {k: v for k, v in VALID.items() if k != 'consent'}
        self.app = MembershipApplication.objects.create(consent=True, **data)

    def test_submission_appears_in_dashboard_and_sidebar(self):
        self.client.force_login(self.admin)
        r = self.client.get(reverse('dashboard'))
        self.assertContains(r, "demande d'adhésion en attente")
        self.assertContains(r, reverse('membership_application_list'))
        self.assertContains(self.client.get(reverse('membership_application_list')), 'Awa Traoré')

    def test_validate_then_revoke_from_backoffice(self):
        self.client.force_login(self.admin)
        for action, expected in (('approve', 'approved'), ('revoke', 'revoked')):
            self.client.post(reverse('membership_application_action', args=[self.app.pk, action]))
            self.app.refresh_from_db()
            self.assertEqual(self.app.status, expected)

    def test_simple_member_forbidden(self):
        self.client.force_login(self.member)
        self.assertEqual(self.client.get(reverse('membership_application_list')).status_code, 302)
        self.client.post(reverse('membership_application_action', args=[self.app.pk, 'approve']))
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, 'pending')

    def test_get_action_not_allowed(self):
        self.client.force_login(self.admin)
        r = self.client.get(reverse('membership_application_action', args=[self.app.pk, 'approve']))
        self.assertEqual(r.status_code, 405)


class MembershipMemberAccountTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user(
            username='adm', password='x', email='adm@x.org', nom='A', prenom='B', role='admin')
        data = {k: v for k, v in VALID.items() if k != 'consent'}
        self.app = MembershipApplication.objects.create(consent=True, **data)

    def test_approve_creates_public_member(self):
        self.app.approve(self.admin)
        m = self.app.member
        self.assertEqual((m.role, m.is_active, m.email, m.nom, m.prenom),
                         ('membre', True, 'awa@example.org', 'AWA', 'Traoré'))
        self.assertFalse(m.has_usable_password())
        self.assertContains(self.client.get(reverse('public_member_list')), 'AWA')

    def test_revoke_hides_member_and_reapprove_restores(self):
        self.app.approve(self.admin)
        self.app.revoke(self.admin, 'x')
        self.app.member.refresh_from_db()
        self.assertFalse(self.app.member.is_active)
        self.assertNotContains(self.client.get(reverse('public_member_list')), 'AWA')
        self.app.approve(self.admin)
        self.app.member.refresh_from_db()
        self.assertTrue(self.app.member.is_active)
        self.assertEqual(get_user_model().objects.filter(email='awa@example.org').count(), 1)

    def test_existing_admin_account_not_downgraded_or_deactivated(self):
        self.app.email = 'adm@x.org'
        self.app.save()
        self.app.approve(self.admin)
        self.app.revoke(self.admin)
        self.admin.refresh_from_db()
        self.assertEqual((self.admin.role, self.admin.is_active), ('admin', True))


class WizardAndProfileTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user(
            username='adm', password='x', email='adm@x.org', nom='A', prenom='B', role='admin')

    def test_how_heard_requires_choice_and_other_needs_detail(self):
        self.assertIn('how_heard_choices', MembershipApplicationForm({**VALID, 'how_heard_choices': []}).errors)
        form = MembershipApplicationForm({**VALID, 'how_heard_choices': ['autre'], 'how_heard': ''})
        self.assertIn('how_heard', form.errors)
        form = MembershipApplicationForm({**VALID, 'how_heard_choices': ['autre'], 'how_heard': 'Une affiche'})
        self.assertTrue(form.is_valid(), form.errors)

    def test_first_error_step(self):
        form = MembershipApplicationForm({**VALID, 'contribution': ''})
        self.assertFalse(form.is_valid())
        self.assertEqual(form.first_error_step(), 2)

    def test_submit_redirects_to_thanks_page(self):
        r = self.client.post(reverse('membership_apply'), VALID)
        self.assertRedirects(r, reverse('membership_thanks'), fetch_redirect_response=False)
        self.assertContains(self.client.get(reverse('membership_thanks')), 'Awa Traoré')
        self.assertEqual(MembershipApplication.objects.get().how_heard_choices, ['collegue', 'site_web'])

    def test_invalid_submit_reopens_wizard_on_error_step(self):
        r = self.client.post(reverse('membership_apply'), {**VALID, 'contribution': ''})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'data-start="2"')

    def test_profile_copied_to_member_and_bio_escaped(self):
        data = {k: v for k, v in VALID.items() if k != 'consent'}
        app = MembershipApplication.objects.create(
            consent=True, bio='Bonjour <script>alert(1)</script>', social_linkedin='https://linkedin.com/in/awa',
            scholar_link='https://scholar.google.com/x', **{**data, 'phone': '+22370000000'})
        app.approve(self.admin)
        m = app.member
        self.assertEqual(m.social_linkedin, 'https://linkedin.com/in/awa')
        self.assertEqual(m.scholar_link, 'https://scholar.google.com/x')
        self.assertEqual(m.phone_number, '+22370000000')
        self.assertNotIn('<script>', m.bio)
        self.assertIn('&lt;script&gt;', m.bio)

    def test_existing_member_data_not_overwritten(self):
        get_user_model().objects.create_user(
            username='awa@example.org', email='awa@example.org', nom='AWA', prenom='T', role='membre',
            social_linkedin='https://linkedin.com/in/old')
        data = {k: v for k, v in VALID.items() if k != 'consent'}
        app = MembershipApplication.objects.create(
            consent=True, social_linkedin='https://linkedin.com/in/new', **data)
        app.approve(self.admin)
        self.assertEqual(app.member.social_linkedin, 'https://linkedin.com/in/old')
