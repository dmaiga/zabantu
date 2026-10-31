from django.test import TestCase
from django.urls import reverse

from users.testing import make_user

from .models import Article, Guelekan


class ArticleBackofficeTests(TestCase):
    def setUp(self):
        self.article = Article.objects.create(title='Une publication', status='draft', content='x')
        self.member = make_user('membre')
        self.moderator = make_user('moderateur')

    def test_list_ignores_removed_category_filter(self):
        self.client.force_login(self.member)
        r = self.client.get(reverse('article_list'), {'category': 'x'})
        self.assertEqual(r.status_code, 200)

    def test_member_cannot_publish_or_delete(self):
        self.client.force_login(self.member)
        self.assertEqual(self.client.post(reverse('publish_article', args=[self.article.slug])).status_code, 403)
        self.assertEqual(self.client.post(reverse('article_delete', args=[self.article.slug])).status_code, 403)
        self.article.refresh_from_db()
        self.assertEqual(self.article.status, 'draft')

    def test_publish_requires_post(self):
        self.client.force_login(self.moderator)
        self.assertEqual(self.client.get(reverse('publish_article', args=[self.article.slug])).status_code, 405)

    def test_moderator_publishes_then_unpublishes(self):
        self.client.force_login(self.moderator)
        self.client.post(reverse('publish_article', args=[self.article.slug]))
        self.article.refresh_from_db()
        self.assertEqual(self.article.status, 'published')
        self.client.post(reverse('unpublish_article', args=[self.article.slug]))
        self.article.refresh_from_db()
        self.assertEqual(self.article.status, 'draft')


class GuelekanBackofficeTests(TestCase):
    def setUp(self):
        self.seminar = Guelekan.objects.create(title='Séminaire', content='<p>x</p>', status='draft')

    def test_member_cannot_publish_or_delete(self):
        self.client.force_login(make_user('membre'))
        self.assertEqual(self.client.post(reverse('publish_guelekan', args=[self.seminar.slug])).status_code, 403)
        self.assertEqual(self.client.post(reverse('guelekan_delete', args=[self.seminar.slug])).status_code, 403)

    def test_moderator_publishes_with_post_only(self):
        self.client.force_login(make_user('moderateur'))
        url = reverse('publish_guelekan', args=[self.seminar.slug])
        self.assertEqual(self.client.get(url).status_code, 405)
        self.client.post(url)
        self.seminar.refresh_from_db()
        self.assertEqual(self.seminar.status, 'published')
