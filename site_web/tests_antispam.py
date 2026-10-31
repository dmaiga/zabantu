import time
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.cache import caches
from django.test import TestCase
from django.urls import reverse

from . import antispam
from .models import ContactMessage, NewsletterSubscriber
from .tests_helpers import human

CONTACT = {'name': 'Traoré', 'last_name': 'Awa', 'email': 'awa@example.org', 'phone': '',
           'subject': 'collaboration', 'message': 'Bonjour, une proposition de collaboration.'}


class AntiSpamBase(TestCase):
    def setUp(self):
        caches['antispam'].clear()


class HoneypotAndTimingTests(AntiSpamBase):
    def post_contact(self, data):
        return self.client.post(reverse('contact'), data, follow=True)

    def test_pages_render_the_trap_and_signed_stamp(self):
        for name in ('contact', 'membership_apply', 'home'):
            html = self.client.get(reverse(name)).content.decode()
            self.assertIn(f'name="{antispam.HONEYPOT}"', html, name)
            self.assertIn(f'name="{antispam.STAMP}"', html, name)

    def test_filled_honeypot_is_rejected_with_clear_message(self):
        r = self.post_contact({**human(CONTACT), antispam.HONEYPOT: 'http://spam.example'})
        self.assertContains(r, 'Envoi refusé')
        self.assertEqual(ContactMessage.objects.count(), 0)

    def test_too_fast_submission_is_rejected(self):
        r = self.post_contact(human(CONTACT, age=0))
        self.assertContains(r, 'trop vite')
        self.assertEqual(ContactMessage.objects.count(), 0)

    def test_missing_or_forged_stamp_is_rejected(self):
        for data in (CONTACT, {**CONTACT, antispam.STAMP: 'forge'}):
            r = self.post_contact(data)
            self.assertContains(r, 'expiré')
        self.assertEqual(ContactMessage.objects.count(), 0)

    def test_expired_stamp_is_rejected(self):
        r = self.post_contact(human(CONTACT, age=antispam.MAX_SECONDS + 60))
        self.assertContains(r, 'expiré')

    def test_human_submission_is_accepted(self):
        self.post_contact(human(CONTACT))
        self.assertEqual(ContactMessage.objects.count(), 1)

    def test_newsletter_validates_email_and_rejects_robots(self):
        r = self.client.post(reverse('newsletter_subscribe'), human({'email': 'pas-un-mail'}), follow=True)
        self.assertContains(r, 'Adresse e-mail invalide')
        r = self.client.post(reverse('newsletter_subscribe'), {'email': 'a@example.org'}, follow=True)
        self.assertContains(r, 'expiré')
        self.assertEqual(NewsletterSubscriber.objects.count(), 0)
        self.client.post(reverse('newsletter_subscribe'), human({'email': 'a@example.org'}))
        self.assertEqual(NewsletterSubscriber.objects.count(), 1)

    def test_no_sending_limit_for_normal_visitors(self):
        for _ in range(8):
            self.client.post(reverse('contact'), human(CONTACT))
        self.assertEqual(ContactMessage.objects.count(), 8)

    def test_wizard_fields_are_untouched_by_trap_fields(self):
        html = self.client.get(reverse('membership_apply')).content.decode()
        self.assertEqual(html.count(f'name="{antispam.HONEYPOT}"'), 1)


class LoginLockoutTests(AntiSpamBase):
    def setUp(self):
        super().setUp()
        self.user = get_user_model().objects.create_user(
            username='adm', password='bon-mot-de-passe', email='adm@x.org', nom='A', prenom='B', role='admin')
        self.url = reverse('login')

    def fail(self, times):
        for _ in range(times):
            r = self.client.post(self.url, {'username': 'adm', 'password': 'faux'}, follow=True)
        return r

    def test_fourth_failure_is_still_a_plain_error(self):
        r = self.fail(4)
        self.assertContains(r, 'Identifiants invalides')

    def test_fifth_failure_blocks_for_five_minutes_even_with_good_password(self):
        r = self.fail(5)
        self.assertContains(r, 'Réessayez dans 5 minutes')
        r = self.client.post(self.url, {'username': 'adm', 'password': 'bon-mot-de-passe'}, follow=True)
        self.assertContains(r, 'Trop de tentatives')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_lock_expires_then_next_lock_is_longer(self):
        self.fail(5)
        later = time.time() + 5 * 60 + 1
        with mock.patch('site_web.antispam.time.time', return_value=later):
            self.assertEqual(antispam.login_wait_seconds('adm'), 0)
            r = self.fail(5)
        self.assertContains(r, 'Réessayez dans 10 minutes')

    def test_success_resets_the_counters(self):
        self.fail(4)
        self.client.post(self.url, {'username': 'adm', 'password': 'bon-mot-de-passe'})
        self.client.logout()
        r = self.fail(4)
        self.assertContains(r, 'Identifiants invalides')

    def test_lock_applies_to_the_identifier_only(self):
        self.fail(5)
        get_user_model().objects.create_user(
            username='autre', password='mdp-autre', email='autre@x.org', nom='C', prenom='D', role='admin')
        r = self.client.post(self.url, {'username': 'autre', 'password': 'mdp-autre'})
        self.assertEqual(r.status_code, 302)
