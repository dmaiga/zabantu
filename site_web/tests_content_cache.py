"""Lot 3 : cache des morceaux de pages publiques, invalidé à chaque changement de contenu."""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from articles.models import Article
from site_web import content_cache


def publish(title, **kw):
    return Article.objects.create(title=title, status='published', content='x', **kw)


@override_settings(PAGE_CACHE_TIMEOUT=600)
class ContentCacheTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_fragment_really_cached(self):
        article = publish('Titre initial')
        self.assertContains(self.client.get(reverse('home')), 'Titre initial')
        Article.objects.filter(pk=article.pk).update(title='Changé sans signal')   # contourne les signaux
        self.assertContains(self.client.get(reverse('home')), 'Titre initial')      # page servie depuis le cache
        self.assertContains(self.client.get(reverse('public_article_list')), 'Changé sans signal')  # liste pas encore en cache

    def test_publication_invalidates_home_and_list(self):
        publish('Premier')
        self.client.get(reverse('home')), self.client.get(reverse('public_article_list'))
        publish('Nouvelle publication')
        self.assertContains(self.client.get(reverse('home')), 'Nouvelle publication')
        self.assertContains(self.client.get(reverse('public_article_list')), 'Nouvelle publication')

    def test_edit_and_delete_invalidate(self):
        article = publish('Avant')
        self.client.get(reverse('home'))
        article.title = 'Après'
        article.save()
        self.assertContains(self.client.get(reverse('home')), 'Après')
        article.delete()
        self.assertNotContains(self.client.get(reverse('home')), 'Après')

    def test_list_varies_with_filters(self):
        publish('Une analyse', article_type='analyse')
        publish('Un rapport', article_type='rapport')
        url = reverse('public_article_list')
        self.assertContains(self.client.get(url + '?type=analyse'), 'Une analyse')
        r = self.client.get(url + '?type=rapport')
        self.assertContains(r, 'Un rapport')
        self.assertNotContains(r, 'Une analyse')

    def test_scheduled_publication_by_cron_invalidates(self):
        Article.objects.create(title='Programmée', status='scheduled', content='x',
                               publish_at=timezone.now() - timedelta(minutes=1))
        self.assertNotContains(self.client.get(reverse('home')), 'Programmée')
        call_command('publish_scheduled', stdout=open('/dev/null', 'w'))
        self.assertContains(self.client.get(reverse('home')), 'Programmée')

    def test_author_change_and_login(self):
        user = get_user_model().objects.create_user(
            username='a', password='x', email='a@x.org', nom='Diallo', prenom='Awa', role='membre')
        article = publish('Avec auteur')
        version = content_cache.content_version()
        article.authors.add(user)                                    # lien plusieurs-à-plusieurs
        self.assertNotEqual(content_cache.content_version(), version)
        version = content_cache.content_version()
        self.client.login(username='a', password='x')                # simple connexion : rien à invalider
        self.assertEqual(content_cache.content_version(), version)

    def test_unrelated_model_does_not_invalidate(self):
        from site_web.models import ContactMessage
        version = content_cache.content_version()
        ContactMessage.objects.create(name='N', email='n@x.org', subject='s', message='m')
        self.assertEqual(content_cache.content_version(), version)


@override_settings(MEDIA_ROOT=__import__('tempfile').mkdtemp())
class ThumbnailSizeCacheTests(TestCase):
    def test_original_opened_once(self):
        import io
        from unittest import mock
        from PIL import Image
        from django.core.files.base import ContentFile
        from django.core.files.storage import default_storage
        from site_web import thumbnails
        cache.clear()
        buf = io.BytesIO()
        Image.new('RGB', (300, 200)).save(buf, 'PNG')
        name = default_storage.save('tests/size-cache.png', ContentFile(buf.getvalue()))
        try:
            with mock.patch.object(thumbnails.Image, 'open', wraps=Image.open) as opened:
                first = thumbnails.get_thumbnail(name, 640)
                second = thumbnails.get_thumbnail(name, 640)
            self.assertEqual(opened.call_count, 1)
            self.assertEqual((first.src_width, first.src_height), (300, 200))
            self.assertEqual(second, first)
        finally:
            default_storage.delete(name)
