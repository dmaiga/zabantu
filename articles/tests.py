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


class ArticleListTests(TestCase):
    def setUp(self):
        self.client.force_login(make_user('moderateur'))
        for i in range(25):
            Article.objects.create(title=f'Etude {i:02d}', status='published' if i % 5 else 'draft',
                                   article_type='analyse' if i % 2 else 'rapport', content='x')

    def test_list_is_paginated(self):
        r = self.client.get(reverse('article_list'))
        self.assertEqual(len(r.context['page_obj']), 20)
        self.assertEqual(r.context['page_obj'].paginator.count, 25)
        self.assertEqual(len(self.client.get(reverse('article_list'), {'page': 2}).context['page_obj']), 5)

    def test_filters_combine_and_survive_pagination(self):
        r = self.client.get(reverse('article_list'), {'type': 'rapport', 'status': 'published'})
        titles = [a.title for a in r.context['page_obj']]
        self.assertTrue(titles)
        self.assertTrue(all(a.article_type == 'rapport' and a.status == 'published' for a in r.context['page_obj']))
        self.assertIn('type=rapport', r.context['querystring'])

    def test_search_matches_the_title(self):
        r = self.client.get(reverse('article_list'), {'q': 'Etude 07'})
        self.assertEqual([a.title for a in r.context['page_obj']], ['Etude 07'])

    def test_invalid_values_are_ignored_not_fatal(self):
        r = self.client.get(reverse('article_list'), {'type': 'nope', 'date_from': 'pas-une-date', 'page': 'x'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context['page_obj'].paginator.count, 25)

    def test_status_tabs_show_counts(self):
        r = self.client.get(reverse('article_list'))
        self.assertEqual(dict((v, n) for v, _, n in r.context['status_tabs'])['draft'], 5)


class DetailPagesTests(TestCase):
    def setUp(self):
        self.client.force_login(make_user('moderateur'))

    def test_article_detail_shows_the_full_content_and_actions_in_the_side_column(self):
        long_text = ' '.join(f'mot{i}' for i in range(120))
        article = Article.objects.create(title='Long', status='draft', content=f'<p>{long_text}</p>')
        r = self.client.get(reverse('article_detail', args=[article.slug]))
        self.assertContains(r, 'mot119')  # plus de troncature à 30 mots
        self.assertContains(r, reverse('publish_article', args=[article.slug]))
        self.assertContains(r, reverse('article_delete', args=[article.slug]))

    def test_member_does_not_see_moderation_buttons(self):
        article = Article.objects.create(title='Long', status='draft', content='x')
        self.client.force_login(make_user('membre'))
        r = self.client.get(reverse('article_detail', args=[article.slug]))
        self.assertNotContains(r, reverse('publish_article', args=[article.slug]))
        self.assertNotContains(r, reverse('article_delete', args=[article.slug]))

    def test_guelekan_detail_renders_for_draft_and_published(self):
        for status in ('draft', 'published'):
            g = Guelekan.objects.create(title=f'S {status}', content='<p>x</p>', status=status)
            r = self.client.get(reverse('guelekan_detail', args=[g.slug]))
            self.assertEqual(r.status_code, 200)
            self.assertContains(r, 'Gɛlɛkan')
