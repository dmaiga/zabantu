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
        self.assertContains(r, "demande d&#x27;adhésion à examiner")
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


class GuelekanFilterTests(TestCase):
    def test_old_list_redirects_to_publications_filter(self):
        r = self.client.get(reverse('public_guelekan_list'))
        self.assertRedirects(r, reverse('public_article_list') + '?type=guelekan', fetch_redirect_response=False)

    def test_guelekan_filter_page_loads(self):
        r = self.client.get(reverse('public_article_list'), {'type': 'guelekan'})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Aucun séminaire trouvé')

    def test_home_has_no_independent_seminar_block(self):
        r = self.client.get(reverse('home'))
        self.assertEqual(r.status_code, 200)
        self.assertNotContains(r, 'Dernier séminaire')


class EventPagesTests(TestCase):
    def setUp(self):
        from datetime import timedelta
        from django.utils import timezone
        from events.models import Event
        self.user = get_user_model().objects.create_user(
            username='ev', password='x', email='ev@x.org', nom='E', prenom='V', role='admin')
        base = dict(content='<p>Contenu</p>', image='events/x.png', status='published',
                    event_type='seminaire', author=self.user)
        self.future = Event.objects.create(title='Futur', date=timezone.now() + timedelta(days=5),
                                           is_webinar=True, webinar_link='https://meet.example/abc', **base)
        self.past = Event.objects.create(title='Passé', date=timezone.now() - timedelta(days=5),
                                         is_webinar=True, webinar_link='https://meet.example/old', **base)

    def test_list_and_filters(self):
        r = self.client.get(reverse('public_event_list'))
        self.assertContains(r, 'Futur')
        self.assertContains(r, 'Passé')
        r = self.client.get(reverse('public_event_list'), {'type': 'formation'})
        self.assertNotContains(r, 'Futur')
        self.assertEqual(self.client.get(reverse('public_event_list'), {'type': 'zzz'}).status_code, 200)

    def test_webinar_link_only_for_upcoming(self):
        self.assertContains(self.client.get(reverse('public_event_detail', args=[self.future.pk])), 'meet.example/abc')
        r = self.client.get(reverse('public_event_detail', args=[self.past.pk]))
        self.assertNotContains(r, 'meet.example/old')
        self.assertContains(r, 'Cet événement est terminé')

    def test_calendar_only_for_upcoming_and_ics_valid(self):
        self.assertContains(self.client.get(reverse('public_event_detail', args=[self.future.pk])), 'Google Agenda')
        self.assertNotContains(self.client.get(reverse('public_event_detail', args=[self.past.pk])), 'Google Agenda')
        r = self.client.get(reverse('public_event_ics', args=[self.future.pk]))
        self.assertEqual(r['Content-Type'], 'text/calendar; charset=utf-8')
        self.assertIn('BEGIN:VEVENT', r.content.decode())
        self.assertIn('SUMMARY:Futur', r.content.decode())


import io
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

_MEDIA = tempfile.mkdtemp()


def _png(name='p.png', size=(40, 30)):
    from PIL import Image
    buf = io.BytesIO()
    Image.new('RGB', size, (90, 140, 90)).save(buf, 'PNG')
    return SimpleUploadedFile(name, buf.getvalue(), content_type='image/png')


@override_settings(MEDIA_ROOT=_MEDIA)
class GalleryPagesTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(_MEDIA, ignore_errors=True)

    def setUp(self):
        from gallery.models import Gallery, Photo, PhotoTag
        self.user = get_user_model().objects.create_user(
            username='g', password='x', email='g@x.org', nom='Maiga', prenom='Dadi', role='admin')
        self.full = Gallery.objects.create(title='Séminaire 2026', created_by=self.user, description='Ligne 1\nLigne 2')
        self.empty = Gallery.objects.create(title='Galerie vide', created_by=self.user)
        self.tag = PhotoTag.objects.create(name='terrain')
        self.p1 = Photo.objects.create(gallery=self.full, title='Première', image=_png('a.png'), uploaded_by=self.user)
        self.p2 = Photo.objects.create(gallery=self.full, title='Seconde', image=_png('b.png'), uploaded_by=self.user)
        self.p2.tags.add(self.tag)

    def test_list_hides_empty_gallery_and_shows_count_and_fallback_cover(self):
        r = self.client.get(reverse('liste_galeries'))
        self.assertContains(r, 'Séminaire 2026')
        self.assertNotContains(r, 'Galerie vide')
        self.assertContains(r, 'galleries/photos/')  # première photo en couverture de secours

    def test_pages_have_their_own_banner_not_the_default_one(self):
        urls = [reverse('liste_galeries'), reverse('detail_galerie', args=[self.full.slug]),
                reverse('toutes_photos'), reverse('detail_photo', args=[self.p1.pk])]
        for url in urls:
            self.assertNotContains(self.client.get(url), 'Bienvenue au groupe de recherche Zabantu', msg_prefix=url)

    def test_detail_uses_viewer_and_whole_photos(self):
        r = self.client.get(reverse('detail_galerie', args=[self.full.slug]))
        self.assertContains(r, 'pswp-gallery')
        self.assertContains(r, 'photo-masonry')
        self.assertContains(r, 'photoswipe')
        self.assertNotContains(r, 'data-lightbox')

    def test_all_photos_filters(self):
        r = self.client.get(reverse('toutes_photos'), {'tag': 'terrain'})
        self.assertContains(r, 'Seconde')
        self.assertNotContains(r, 'Première</figcaption>')
        r = self.client.get(reverse('toutes_photos'), {'gallery': 'inexistante'})
        self.assertContains(r, 'Aucune photo pour cette sélection')

    def test_photo_detail_navigation_and_author_name(self):
        # p2 est la plus récente : elle a une « suivante » (p1) mais pas de « précédente »
        r2 = self.client.get(reverse('detail_photo', args=[self.p2.pk]))
        self.assertContains(r2, 'Photo suivante')
        self.assertNotContains(r2, 'Photo précédente')
        r1 = self.client.get(reverse('detail_photo', args=[self.p1.pk]))
        self.assertContains(r1, 'Photo précédente')
        self.assertNotContains(r1, 'Photo suivante')
        self.assertContains(r2, 'Dadi')               # nom complet affiché
        self.assertNotContains(r2, '>g<')             # pas l'identifiant de connexion

    def test_event_detail_has_proper_banner(self):
        from datetime import timedelta
        from django.utils import timezone
        from events.models import Event
        e = Event.objects.create(title='Évt', content='x', image='events/x.png', status='published',
                                 date=timezone.now() + timedelta(days=1), author=self.user)
        r = self.client.get(reverse('public_event_detail', args=[e.pk]))
        self.assertNotContains(r, 'Bienvenue au groupe de recherche Zabantu')
        self.assertContains(r, 'Nos Événements')


@override_settings(MEDIA_ROOT=_MEDIA)
class ThumbnailTests(TestCase):
    def setUp(self):
        from gallery.models import Gallery, Photo
        self.user = get_user_model().objects.create_user(
            username='t', password='x', email='t@x.org', nom='T', prenom='T', role='admin')
        self.gallery = Gallery.objects.create(title='Grande', created_by=self.user)
        self.big = Photo.objects.create(gallery=self.gallery, title='Grande photo',
                                        image=_png('big.png', (1600, 1000)), uploaded_by=self.user)
        self.small = Photo.objects.create(gallery=self.gallery, title='Petite',
                                          image=_png('small.png', (300, 200)), uploaded_by=self.user)

    def _original_bytes(self, photo):
        with photo.image.open('rb') as fh:
            return fh.read()

    def test_thumbnail_created_and_original_untouched(self):
        from site_web.thumbnails import get_thumbnail
        before = self._original_bytes(self.big)
        t = get_thumbnail(self.big.image, 640)
        self.assertIn('cache/thumbs/640/', t.url)
        self.assertEqual((t.width, t.height, t.src_width, t.src_height), (640, 400, 1600, 1000))
        self.assertEqual(self._original_bytes(self.big), before)          # original intact
        self.assertTrue(self.big.image.storage.exists(self.big.image.name))
        self.assertEqual(get_thumbnail(self.big.image, 640).url, t.url)    # idempotent

    def test_small_image_served_as_is(self):
        from site_web.thumbnails import get_thumbnail
        t = get_thumbnail(self.small.image, 640)
        self.assertNotIn('cache/thumbs', t.url)
        self.assertEqual((t.src_width, t.src_height), (300, 200))

    def test_failures_fall_back_to_original(self):
        from unittest import mock
        from site_web.thumbnails import get_thumbnail
        from django.core.files.storage import FileSystemStorage
        with mock.patch.object(FileSystemStorage, 'save', side_effect=OSError('lecture seule')):
            t = get_thumbnail(self.big.image, 480)
        self.assertNotIn('cache/thumbs', t.url)                            # repli sur l'original
        self.assertTrue(t.url.endswith('.png'))
        self.assertEqual(get_thumbnail('inexistant/fichier.png', 640).url, '/media/inexistant/fichier.png')
        self.assertEqual(get_thumbnail(None, 640).url, '')

    def test_pages_use_thumbnails_and_keep_original_for_viewer(self):
        r = self.client.get(reverse('detail_galerie', args=[self.gallery.slug]))
        self.assertContains(r, 'cache/thumbs/640/')
        self.assertContains(r, 'data-pswp-width="1600"')
        self.assertContains(r, 'galleries/photos/')                        # lien vers l'original conservé
        self.assertEqual(self.client.get(reverse('detail_photo', args=[self.big.pk])).status_code, 200)

    def test_management_command(self):
        from django.core.management import call_command
        out = io.StringIO()
        call_command('generate_thumbnails', '--width', '320', stdout=out)
        self.assertIn('image(s) traitée(s)', out.getvalue())
        self.assertTrue(self.big.image.storage.exists(self.big.image.name))


class ContactPageTests(TestCase):
    def test_layout_and_links(self):
        r = self.client.get(reverse('contact'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'href="tel:+22377941470"')
        self.assertContains(r, 'href="mailto:info@zabantu.net"')
        self.assertContains(r, 'Nos coordonnées')
        self.assertNotContains(r, 'fa-twitter')           # lien mort retiré
        content = r.content.decode().split('class="contact-wrap"', 1)[1]
        self.assertNotIn('href="#"', content)            # plus aucun lien factice dans la page

    def test_invalid_post_shows_errors_in_form(self):
        r = self.client.post(reverse('contact'), {'name': '', 'email': 'pas-un-mail'})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'field-error')
        self.assertContains(r, 'Veuillez corriger les erreurs')


class ContactWithoutCaptchaTests(TestCase):
    def test_valid_message_saved_without_captcha(self):
        from .models import ContactMessage
        r = self.client.post(reverse('contact'), {
            'name': 'Traoré', 'last_name': 'Awa', 'email': 'awa@example.org', 'phone': '',
            'subject': 'collaboration', 'message': 'Bonjour, une proposition de collaboration.'})
        self.assertRedirects(r, reverse('contact'), fetch_redirect_response=False)
        self.assertEqual(ContactMessage.objects.count(), 1)

    def test_no_captcha_field_rendered(self):
        r = self.client.get(reverse('contact'))
        self.assertNotContains(r, 'captcha')
