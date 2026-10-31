from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.urls import reverse

from site_web.models import NewsletterCampaign, NewsletterSubscriber
from users.testing import make_user


@override_settings(DEBUG=True)
class SeedNewsletterDemoTests(TestCase):
    def setUp(self):
        self.admin = make_user('admin', is_superuser=True)

    def run_seed(self, *args):
        call_command('seed_newsletter_demo', *args, stdout=StringIO())

    def test_creates_every_campaign_status_and_screens_render(self):
        self.run_seed()
        statuses = set(NewsletterCampaign.objects.values_list('status', flat=True))
        self.assertEqual(statuses, {'draft', 'sent', 'partial', 'failed', 'sending', 'cancelled'})
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(reverse('newsletter_list')), '[démo]')
        self.assertEqual(self.client.get(reverse('email_delivery_list')).status_code, 200)

    def test_reset_recreates_without_duplicates_and_plain_rerun_is_refused(self):
        self.run_seed()
        with self.assertRaises(CommandError):
            self.run_seed()
        self.run_seed('--reset')
        self.assertEqual(NewsletterCampaign.objects.count(), 6)
        self.assertEqual(NewsletterSubscriber.objects.filter(email__endswith='@demo.zabantu.test').count(), 14)

    @override_settings(DEBUG=False)
    def test_refused_outside_debug(self):
        with self.assertRaises(CommandError):
            self.run_seed()
