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


class ProductionParityTests(TestCase):
    """Le dépôt reprend l'état de la production : migrations 0008-0010, champs « ouvrage », liste de types."""

    def test_migration_history_matches_production_and_has_a_single_head(self):
        from django.db.migrations.loader import MigrationLoader
        loader = MigrationLoader(None, ignore_no_migrations=True)
        names = {name for app, name in loader.graph.nodes if app == 'articles'}
        for expected in ('0008_alter_article_article_type', '0009_article_page_count_article_publication_date_and_more',
                         '0010_alter_article_article_type', '0011_scheduled_status'):
            self.assertIn(expected, names)
        self.assertEqual(loader.graph.leaf_nodes('articles'), [('articles', '0011_scheduled_status')])
        self.assertEqual(loader.graph.node_map[('articles', '0011_scheduled_status')].parents.pop(),
                         ('articles', '0010_alter_article_article_type'))

    def test_models_have_no_pending_migration(self):
        from io import StringIO
        from django.core.management import call_command
        call_command('makemigrations', check=True, dry_run=True, stdout=StringIO())

    def test_book_fields_exist_and_zabantu_analyse_left_the_model_choices(self):
        fields = {f.name for f in Article._meta.get_fields()}
        self.assertTrue({'publisher_book', 'publication_place', 'page_count', 'publication_date'} <= fields)
        values = [v for v, _ in Article.ARTICLE_TYPE_CHOICES]
        self.assertNotIn('zabantu', values)
        self.assertNotIn('analyse', values)

    def test_menu_offers_analyse_and_ouvrage_and_labels_them(self):
        self.client.force_login(make_user('moderateur'))
        r = self.client.get(reverse('article_list'))
        for value in ('analyse', 'ouvrage', 'academic', 'policy', 'rapport', 'working', 'independent'):
            self.assertContains(r, f'?type={value}"')
        self.assertNotContains(r, '?type=zabantu"')
        self.assertEqual(Article(article_type='analyse').type_label, 'Analyse')
        self.assertEqual(Article(article_type='academic').type_label, 'Article')

    def test_authors_are_merged_internal_external_and_academic(self):
        member = make_user('membre')
        article = Article.objects.create(title='T', content='x', external_author='Dr X', academic_authors='Pr Y')
        article.authors.add(member)
        self.assertEqual([a['type'] for a in article.get_display_authors()], ['zabantu', 'external', 'academic'])


class OuvrageTests(TestCase):
    def setUp(self):
        self.client.force_login(make_user('moderateur'))

    def data(self, **kw):
        base = {'title': 'Penser l\'État', 'subtitle': 'Essai', 'academic_authors': 'Collectif',
                'publisher_book': 'Éditions du Sahel', 'publication_place': 'Bamako', 'page_count': '312',
                'publication_date': '2025-06-15', 'resume': '<p>Résumé</p>'}
        base.update(kw)
        return base

    def test_ouvrage_is_created_with_its_book_fields(self):
        r = self.client.post(reverse('article_create') + '?type=ouvrage', {**self.data(), 'article_type': 'ouvrage'})
        book = Article.objects.get(title="Penser l'État")
        self.assertRedirects(r, reverse('article_detail', args=[book.slug]), fetch_redirect_response=False)
        self.assertEqual((book.article_type, book.publisher_book, book.page_count, str(book.publication_date)),
                         ('ouvrage', 'Éditions du Sahel', 312, '2025-06-15'))

    def test_publisher_date_and_an_author_are_required(self):
        from articles.forms import OuvrageForm
        form = OuvrageForm(data=self.data(publisher_book='', publication_date='', academic_authors=''))
        self.assertFalse(form.is_valid())
        self.assertIn('publisher_book', form.errors)
        self.assertIn('publication_date', form.errors)
        self.assertIn('au moins un auteur', str(form.non_field_errors()).lower())
        self.assertTrue(OuvrageForm().fields['publisher_book'].required)

    def test_page_shows_the_book_fields_in_the_references_step(self):
        r = self.client.get(reverse('article_create') + '?type=ouvrage')
        for name in ('publisher_book', 'publication_place', 'page_count', 'publication_date'):
            self.assertContains(r, f'name="{name}"')
        self.assertNotContains(r, 'name="journal"')

    def test_editing_an_existing_ouvrage_keeps_its_data_and_shows_it(self):
        import datetime
        book = Article.objects.create(title='Ouvrage existant', article_type='ouvrage', status='draft', content='x',
                                      publisher_book='PUF', page_count=250, publication_date=datetime.date(2024, 1, 2),
                                      academic_authors='A. Auteur')
        r = self.client.get(reverse('article_update', args=[book.slug]))
        self.assertContains(r, 'value="PUF"')
        self.assertContains(r, 'value="2024-01-02"')
        self.client.post(reverse('article_update', args=[book.slug]), self.data(title='Ouvrage existant', publisher_book='PUF',
                         page_count='250', publication_date='2024-01-02', academic_authors='A. Auteur'))
        book.refresh_from_db()
        self.assertEqual((book.page_count, book.publisher_book), (250, 'PUF'))
        detail = self.client.get(reverse('article_detail', args=[book.slug]))
        self.assertContains(detail, 'PUF')
        self.assertContains(detail, '250')


class EitherOrAuthorRuleTests(TestCase):
    def test_an_external_author_alone_is_enough_for_academic_working_and_ouvrage(self):
        from articles.forms import AcademicForm, OuvrageForm, WorkingPaperForm
        academic = AcademicForm(data={'title': 'A', 'abstract': 'x', 'journal': 'J', 'publication_year': 2024,
                                      'academic_authors': 'Dr Externe'})
        working = WorkingPaperForm(data={'title': 'W', 'resume': 'x', 'institution': 'I', 'working_number': '1',
                                         'working_year': 2024, 'academic_authors': 'Dr Externe'})
        ouvrage = OuvrageForm(data={'title': 'O', 'publisher_book': 'P', 'publication_date': '2025-01-01',
                                    'academic_authors': 'Dr Externe'})
        for form in (academic, working, ouvrage):
            self.assertTrue(form.is_valid(), (form.__class__.__name__, form.errors))

    def test_a_member_alone_is_enough_too(self):
        from articles.forms import AcademicForm
        member = make_user('membre')
        form = AcademicForm(data={'title': 'A', 'abstract': 'x', 'journal': 'J', 'publication_year': 2024,
                                  'authors': [member.pk]})
        self.assertTrue(form.is_valid(), form.errors)

    def test_zabantu_style_articles_still_require_a_member(self):
        from articles.forms import ArticleForm
        self.assertTrue(ArticleForm().fields['authors'].required)
