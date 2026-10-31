import re
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from articles.forms import AcademicForm, ArticleForm, GuelekanForm, IndependentForm, WorkingPaperForm
from articles.models import Article, Guelekan
from events.forms import EventForm
from events.models import Event
from users.forms import CustomMemberCreationForm, CustomUserUpdateForm, PartenaireForm
from users.models import Partenaire
from users.testing import make_user


class SectionsKeepEveryFieldTests(TestCase):
    """Un champ oublié dans les sections doit quand même s'afficher : rien ne disparaît silencieusement."""

    def assert_all_fields_shown(self, form):
        shown = {f.name for _, fields in form.grouped_fields() for f in fields}
        visible = {n for n, f in form.fields.items() if not f.widget.is_hidden}
        self.assertEqual(shown, visible, form.__class__.__name__)

    def test_every_form_shows_all_its_visible_fields(self):
        for form_class in (ArticleForm, AcademicForm, IndependentForm, WorkingPaperForm, GuelekanForm,
                           EventForm, CustomMemberCreationForm, PartenaireForm):
            self.assert_all_fields_shown(form_class())
        self.assert_all_fields_shown(CustomUserUpdateForm(editor=make_user('admin')))

    def test_privileged_fields_are_dropped_for_plain_editors(self):
        form = CustomUserUpdateForm(editor=make_user('membre'))
        names = {f.name for _, fields in form.grouped_fields() for f in fields}
        self.assertFalse(names & {'role', 'is_active', 'backoffice_access', 'date_started'})


class FormPagesRenderTests(TestCase):
    def setUp(self):
        self.admin = make_user('admin')
        self.client.force_login(self.admin)

    def test_create_pages_use_the_common_layout(self):
        pages = [reverse('event_create'), reverse('guelekan_create'), reverse('create_member'),
                 reverse('partenaire_create'), reverse('article_create') + '?type=zabantu',
                 reverse('article_create') + '?type=academic']
        for url in pages:
            r = self.client.get(url)
            self.assertEqual(r.status_code, 200, url)
            self.assertContains(r, 'data-submit', msg_prefix=url)
            self.assertContains(r, 'form-control', msg_prefix=url)

    def test_required_marker_and_inline_errors(self):
        r = self.client.post(reverse('partenaire_create'), {'name': ''})
        self.assertContains(r, 'invalid-feedback')
        self.assertContains(r, 'text-danger')  # astérisque des champs obligatoires

    def test_edit_pages_render(self):
        event = Event.objects.create(title='E', content='x', image='x.jpg', date=timezone.now() + timedelta(days=1))
        seminar = Guelekan.objects.create(title='G', content='<p>x</p>')
        article = Article.objects.create(title='A', content='x')
        partner = Partenaire.objects.create(name='P', logo='partenaires/p.png')
        member = make_user('membre')
        for url in (reverse('event_update', args=[event.id]), reverse('guelekan_update', args=[seminar.slug]),
                    reverse('article_update', args=[article.slug]), reverse('partenaire_update', args=[partner.pk]),
                    reverse('update_user', args=[member.pk])):
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_rich_text_fields_use_the_same_editor_everywhere(self):
        for form in (ArticleForm(), GuelekanForm(), EventForm()):
            self.assertEqual(form.fields['content'].widget.__class__.__name__, 'SummernoteWidget')


class FormSubmissionsStillWorkTests(TestCase):
    def setUp(self):
        self.client.force_login(make_user('admin'))

    def png(self, name='img.png'):
        import io
        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image
        buffer = io.BytesIO()
        Image.new('RGB', (20, 20), 'green').save(buffer, 'PNG')
        return SimpleUploadedFile(name, buffer.getvalue(), content_type='image/png')

    def test_event_is_created_as_a_draft_with_rich_content(self):
        with self.settings(MEDIA_ROOT=self.tmp()):
            self.client.post(reverse('event_create'), {
                'title': 'Conférence', 'event_type': 'conference', 'content': '<p>Programme</p>', 'location': 'Bamako',
                'date': (timezone.now() + timedelta(days=5)).strftime('%Y-%m-%dT%H:%M'),
                'image': self.png(),
            })
        event = Event.objects.get(title='Conférence')
        self.assertEqual((event.status, event.content), ('draft', '<p>Programme</p>'))

    def test_event_rules_are_shown_as_a_form_level_error(self):
        r = self.client.post(reverse('event_create'), {
            'title': 'Sans lieu', 'event_type': 'conference', 'content': 'x',
            'date': (timezone.now() + timedelta(days=5)).strftime('%Y-%m-%dT%H:%M')})
        self.assertContains(r, 'Un lieu est requis')

    def test_event_without_image_comes_back_with_the_error(self):
        r = self.client.post(reverse('event_create'), {
            'title': 'Sans image', 'event_type': 'conference', 'content': 'x', 'location': 'Bamako',
            'date': (timezone.now() + timedelta(days=5)).strftime('%Y-%m-%dT%H:%M')})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'invalid-feedback')
        self.assertFalse(Event.objects.filter(title='Sans image').exists())

    def tmp(self):
        import tempfile
        d = tempfile.mkdtemp()
        self.addCleanup(__import__('shutil').rmtree, d, True)
        return d

    def test_guelekan_is_created_through_the_new_form(self):
        r = self.client.post(reverse('guelekan_create'), {
            'title': 'Séminaire X', 'content': '<p>Contenu</p>', 'status': 'draft'})
        seminar = Guelekan.objects.get(title='Séminaire X')
        self.assertRedirects(r, reverse('guelekan_detail', args=[seminar.slug]), fetch_redirect_response=False)

    def test_member_is_created_without_access_by_default(self):
        self.client.post(reverse('create_member'), {'email': 'n@test.org', 'nom': 'Doe', 'prenom': 'Jane'})
        from django.contrib.auth import get_user_model
        self.assertFalse(get_user_model().objects.get(email='n@test.org').backoffice_access)

    def test_partner_is_created(self):
        with self.settings(MEDIA_ROOT=self.tmp()):
            r = self.client.post(reverse('partenaire_create'),
                                 {'name': 'Nouveau', 'order': 1, 'is_active': 'on', 'logo': self.png('logo.png')})
        self.assertRedirects(r, reverse('partenaire_list'))
        self.assertTrue(Partenaire.objects.filter(name='Nouveau', is_active=True).exists())


class WizardMarkupTests(TestCase):
    """La logique des étapes tourne dans le navigateur ; ici on vérifie ce que le serveur fournit."""

    def setUp(self):
        self.client.force_login(make_user('admin'))

    def test_multi_section_form_gets_a_stepper_with_one_entry_per_section(self):
        r = self.client.get(reverse('event_create'))
        self.assertContains(r, 'data-wizard="on"')
        self.assertContains(r, 'data-goto=', count=3)
        self.assertContains(r, 'class="card mb-4 wizard-step"', count=3)

    def test_without_javascript_every_section_is_in_the_page(self):
        r = self.client.get(reverse('guelekan_create'))
        for title in ('Séminaire', 'Invités et galeries', 'Publication'):
            self.assertContains(r, title)

    def test_editing_is_flagged_so_save_stays_available_on_every_step(self):
        event = Event.objects.create(title='E', content='x', image='x.jpg', date=timezone.now() + timedelta(days=1))
        self.assertContains(self.client.get(reverse('event_update', args=[event.id])), 'data-editing="yes"')
        self.assertNotContains(self.client.get(reverse('event_create')), 'data-editing="yes"')

    def test_the_step_holding_an_error_is_flagged(self):
        r = self.client.post(reverse('guelekan_create'), {'title': 'Sans contenu', 'status': 'draft'})
        html = r.content.decode()
        self.assertEqual(html.count('data-has-error="yes"'), 1)
        self.assertIn('Séminaire', html.split('data-has-error="yes"')[1][:200])


class RequiredFieldsAreAnnouncedTests(TestCase):
    """Un champ obligatoire doit le dire avant l'envoi (astérisque + attribut HTML), pas seulement après une erreur."""

    def required(self, form_class):
        form = form_class()
        return {name for name, field in form.fields.items() if field.required}

    def test_academic_publication_announces_journal_and_year(self):
        form = AcademicForm()
        self.assertTrue(form.fields['journal'].required and form.fields['publication_year'].required)
        self.assertFalse(form.fields['publisher'].required)

    def test_each_type_announces_its_own_required_fields(self):
        self.assertTrue({'external_author', 'external_link'} <= self.required(IndependentForm))
        self.assertTrue({'institution', 'working_number', 'working_year'} <= self.required(WorkingPaperForm))
        self.assertIn('authors', self.required(ArticleForm))

    def test_page_shows_the_asterisk_and_the_html_required_attribute(self):
        self.client.force_login(make_user('admin'))
        r = self.client.get(reverse('article_create') + '?type=academic')
        html = r.content.decode()
        label = html.split('for="id_journal"')[1][:200]
        self.assertIn('text-danger', label)
        self.assertRegex(html, r'<input[^>]*name="journal"[^>]*required')
        self.assertContains(r, 'Champ obligatoire')

    def test_missing_required_fields_get_the_standard_message(self):
        self.client.force_login(make_user('admin'))
        r = self.client.post(reverse('article_create') + '?type=academic', {
            'article_type': 'academic', 'title': 'Sans revue', 'abstract': 'x', 'academic_authors': 'Dr X'})
        form = r.context['form']
        self.assertIn('journal', form.errors)
        self.assertIn('publication_year', form.errors)
        self.assertNotIn('Journal obligatoire', str(form.errors))

    def test_either_or_author_rule_is_explained_on_both_fields_and_enforced(self):
        form = AcademicForm(data={'title': 'T', 'abstract': 'x', 'journal': 'J', 'publication_year': 2024})
        self.assertFalse(form.is_valid())
        self.assertIn('au moins un auteur', str(form.non_field_errors()).lower())
        self.assertIn('Au moins un auteur', AcademicForm().fields['academic_authors'].help_text)
        self.assertIn('Au moins un auteur', AcademicForm().fields['authors'].help_text)


class RemainingScreensTests(TestCase):
    """Intervenants, galeries, profil : mêmes listes, formulaires et droits que le reste du backoffice."""

    def setUp(self):
        self.moderator = make_user('moderateur')
        self.client.force_login(self.moderator)

    def person(self, n=0, **kw):
        from intervenants.models import Intervenant
        return Intervenant.objects.create(first_name=f'Prenom{n}', last_name=f'Nom{n}', email=f'i{n}@t.org',
                                          organization='Université', bio='b', intervenant_type='speaker', **kw)

    def test_intervenant_list_is_paginated_filtered_and_searchable(self):
        for i in range(23):
            self.person(i, is_available=(i % 2 == 0))
        r = self.client.get(reverse('intervenant_list'))
        self.assertEqual((len(r.context['page_obj']), r.context['page_obj'].paginator.count), (20, 23))
        free = self.client.get(reverse('intervenant_list'), {'availability': 'available'}).context['page_obj']
        self.assertTrue(all(p.is_available for p in free))
        found = self.client.get(reverse('intervenant_list'), {'q': 'Nom7', 'type': 'nope'}).context['page_obj']
        self.assertEqual([p.last_name for p in found], ['Nom7'])

    def test_intervenant_form_uses_the_wizard_and_creates(self):
        r = self.client.get(reverse('intervenant_create'))
        self.assertContains(r, 'data-goto=', count=4)
        r = self.client.post(reverse('intervenant_create'), {
            'first_name': 'Aminata', 'last_name': 'Cissé', 'email': 'a@t.org', 'organization': 'U',
            'bio': 'bio', 'intervenant_type': 'expert', 'is_available': 'on'})
        from intervenants.models import Intervenant
        self.assertTrue(Intervenant.objects.filter(email='a@t.org').exists())

    def test_deleting_an_intervenant_needs_post_and_a_moderator(self):
        from intervenants.models import Intervenant
        person = self.person()
        url = reverse('intervenant_delete', args=[person.id])
        self.assertEqual(self.client.get(url).status_code, 405)
        self.client.force_login(make_user('membre'))
        self.assertEqual(self.client.post(url).status_code, 403)
        self.client.force_login(self.moderator)
        self.client.post(url)
        self.assertFalse(Intervenant.objects.filter(pk=person.pk).exists())

    def test_gallery_form_and_permissions(self):
        from gallery.models import Gallery
        r = self.client.post(reverse('gallery_create'), {'title': 'Ma galerie', 'description': 'd'})
        gallery = Gallery.objects.get(title='Ma galerie')
        self.assertEqual(self.client.get(reverse('gallery_update', args=[gallery.slug])).status_code, 200)
        self.client.force_login(make_user('membre'))
        self.assertEqual(self.client.post(reverse('gallery_delete', args=[gallery.slug])).status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get(reverse('gallery_update', args=[gallery.slug])).status_code, 302)

    def test_a_moderator_can_edit_a_galery_created_by_someone_else(self):
        from gallery.models import Gallery
        gallery = Gallery.objects.create(title='Des autres', created_by=make_user('membre'))
        self.assertEqual(self.client.get(reverse('gallery_update', args=[gallery.slug])).status_code, 200)

    def test_profile_edit_uses_the_common_form(self):
        r = self.client.get(reverse('profile_edit'))
        self.assertContains(r, 'data-goto=', count=4)
        self.assertContains(r, 'Champ obligatoire')


class CommunicationSectionTests(TestCase):
    def setUp(self):
        self.client.force_login(make_user('moderateur'))

    def test_every_communication_screen_shares_the_same_tabs(self):
        for name in ('contact_message_list', 'sent_messages_list', 'newsletter_list', 'newsletter_campaign_list'):
            r = self.client.get(reverse(name))
            self.assertContains(r, 'Messages reçus', msg_prefix=name)
            self.assertContains(r, "Campagnes d'info-lettre", msg_prefix=name)

    def test_the_word_newsletter_is_gone_from_the_backoffice(self):
        for name in ('contact_message_list', 'newsletter_list', 'newsletter_campaign_list', 'dashboard'):
            html = self.client.get(reverse(name)).content.decode()
            visible = re.sub(r'(href|action|class|id|name)="[^"]*"', '', html)
            self.assertNotIn('Newsletter', visible, name)

    def test_unread_count_shows_in_the_menu_and_tabs(self):
        from site_web.models import ContactMessage
        ContactMessage.objects.create(name='A', last_name='B', email='a@b.org', subject='S', message='m')
        html = self.client.get(reverse('dashboard')).content.decode()
        self.assertIn('Communication', html)
        self.assertIn('badge bg-danger">1<', html.replace('\n', '').replace('  ', ''))


class WizardScriptGuardTests(TestCase):
    def test_done_state_is_toggled_with_a_real_boolean(self):
        """classList.toggle(x, undefined) bascule au lieu de retirer : les étapes non visitées s'affichaient « terminées »."""
        from pathlib import Path
        source = Path(__file__).resolve().parent.joinpath('templates', 'form_page.html').read_text(encoding='utf-8')
        self.assertIn("toggle('is-done', !!(visited[i]", source)

    def test_message_badge_stays_on_the_same_line_in_the_menu(self):
        self.client.force_login(make_user('moderateur'))
        from site_web.models import ContactMessage
        ContactMessage.objects.create(name='A', last_name='B', email='a@b.org', subject='S', message='m')
        html = self.client.get(reverse('dashboard')).content.decode()
        self.assertIn('justify-content:space-between', html.split('Communication</span>')[0][-300:])
