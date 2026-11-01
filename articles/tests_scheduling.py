from datetime import timedelta

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from articles.models import Article


class ScheduledPublicationTests(TestCase):
    """La publication programmée ne dépend que de la commande publish_scheduled (cron), plus d'un middleware."""

    def setUp(self):
        self.article = Article.objects.create(
            title='Programmé', article_type='analyse', content='x', status='scheduled',
            publish_at=timezone.now() - timedelta(minutes=2))

    def test_a_page_visit_does_not_write_to_the_database(self):
        self.client.get(reverse('home'))
        self.article.refresh_from_db()
        self.assertEqual(self.article.status, 'scheduled')
        self.assertEqual(self.client.get(reverse('public_article_detail', args=[self.article.slug])).status_code, 404)

    def test_publish_scheduled_publishes_the_due_article(self):
        call_command('publish_scheduled', stdout=open('/dev/null', 'w'))
        self.article.refresh_from_db()
        self.assertEqual(self.article.status, 'published')
        self.assertEqual(self.client.get(reverse('public_article_detail', args=[self.article.slug])).status_code, 200)
