"""Lot 5 : formations (comptes participants, cours, cohortes, inscriptions, annonces)."""
import re
import shutil
import tempfile
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils import timezone, translation

from site_web.tests_helpers import human
from users.testing import make_user

from . import mailing
from .models import Cohort, CohortAnnouncement, Course, CourseFile, Enrollment, ParticipantProfile

User = get_user_model()
_PRIVATE = tempfile.mkdtemp()
PASSWORD = 'Un-mot-de-passe-solide-42'


def en(name, *args):
    with translation.override('en'):
        return reverse(name, args=args)


def participant(email='awa@example.org', language='fr', active=True, notify=True):
    user = User.objects.create_user(username=email, email=email, password=PASSWORD, prenom='Awa', nom='Traoré',
                                    role='participant', is_active=active)
    ParticipantProfile.objects.create(user=user, status='professionnel', organization='ONG Sahel',
                                      language=language, notify_cohorts=notify)
    return user


def cohort(name='Méthodes quantitatives', days_open=(-1, 10), **kw):
    today = timezone.localdate()
    return Cohort.objects.create(name=name, opens_on=today + timedelta(days=days_open[0]),
                                 closes_on=today + timedelta(days=days_open[1]), **kw)


def pdf(name='cours.pdf'):
    return SimpleUploadedFile(name, b'%PDF-1.4 test', content_type='application/pdf')


SIGNUP = {'prenom': 'Moussa', 'nom': 'Diarra', 'email': 'Moussa@Example.org', 'status': 'professionnel',
          'organization': 'Banque', 'password1': PASSWORD, 'password2': PASSWORD, 'consent': 'on'}


class SignupAndLoginTests(TestCase):
    def test_signup_creates_an_inactive_participant_and_sends_the_confirmation(self):
        r = self.client.post(reverse('participant_signup'), human(SIGNUP))
        self.assertRedirects(r, reverse('participant_signup_done'))
        user = User.objects.get(email='moussa@example.org')
        self.assertEqual((user.role, user.is_active, user.username), ('participant', False, 'moussa@example.org'))
        self.assertEqual((user.participant_profile.status, user.participant_profile.language), ('professionnel', 'fr'))
        self.assertEqual(mail.outbox[-1].subject, 'Confirmez votre compte Zabantu')
        link = re.search(r'http://testserver(/zabantu/compte/confirmer/[^"]+/)', mail.outbox[-1].alternatives[0][0]).group(1)
        r = self.client.get(link)
        self.assertRedirects(r, reverse('participant_space'))
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.client.logout()
        r = self.client.get(link)                                # lien à usage unique
        self.assertRedirects(r, reverse('login'))

    def test_signup_from_the_english_site(self):
        self.client.post(en('participant_signup'), human(SIGNUP))
        self.assertEqual(User.objects.get().participant_profile.language, 'en')
        self.assertEqual(mail.outbox[-1].subject, 'Confirm your Zabantu account')
        self.assertIn('/en/zabantu/compte/confirmer/', mail.outbox[-1].alternatives[0][0])

    def test_signup_keeps_the_training_destination_until_confirmation(self):
        destination = reverse('training_enroll', args=[42])
        self.client.post(reverse('participant_signup'), {**human(SIGNUP), 'next': destination})
        user = User.objects.get()
        token = mailing.confirmation_token.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        self.assertRedirects(self.client.get(reverse('participant_confirm', args=[uid, token])), destination,
                             fetch_redirect_response=False)

    def test_signup_rejects_an_external_destination(self):
        self.client.post(reverse('participant_signup'), {**human(SIGNUP), 'next': 'https://example.net/steal'})
        user = User.objects.get()
        token = mailing.confirmation_token.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        self.assertRedirects(self.client.get(reverse('participant_confirm', args=[uid, token])),
                             reverse('participant_space'))

    def test_email_already_used(self):
        User.objects.filter(pk=make_user('membre').pk).update(email='moussa@example.org')
        r = self.client.post(reverse('participant_signup'), human(SIGNUP))
        self.assertContains(r, 'Un compte existe déjà avec cette adresse')

    def test_single_login_sends_participants_to_their_space(self):
        participant(active=False)
        r = self.client.post(reverse('login'), {'identifier': 'awa@example.org', 'password': PASSWORD})
        self.assertContains(r, "pas encore confirmée")
        User.objects.filter(email='awa@example.org').update(is_active=True)
        r = self.client.post(reverse('login'), {'identifier': 'AWA@example.org', 'password': PASSWORD})
        self.assertRedirects(r, reverse('participant_space'))

    def test_single_login_sends_the_team_to_the_backoffice(self):
        User.objects.filter(pk=make_user('moderateur').pk).update(email='modo@example.org')
        for identifier in ('modo@example.org', User.objects.get(email='modo@example.org').username):
            self.client.logout()
            r = self.client.post(reverse('login'), {'identifier': identifier, 'password': 'secret-pass-123'})
            self.assertRedirects(r, reverse('dashboard'), fetch_redirect_response=False, msg_prefix=identifier)

    def test_old_participant_login_address_redirects(self):
        self.assertRedirects(self.client.get('/en/zabantu/compte/connexion/?next=/x/'), '/en/zabantu/connexion/?next=/x/',
                             fetch_redirect_response=False)

    def test_password_reset_email_points_to_the_public_pages(self):
        participant()
        self.client.post(en('participant_password_reset'), {'email': 'awa@example.org'})
        self.assertIn('/en/zabantu/compte/mot-de-passe/', mail.outbox[-1].body)


class ParticipantIsolationTests(TestCase):
    def setUp(self):
        self.user = participant()
        self.client.force_login(self.user, backend='courses.backends.ParticipantBackend')

    def test_participant_cannot_enter_the_backoffice(self):
        for path in ('/users/dashboard/', reverse('article_create'), reverse('event_list'), reverse('course_admin_list')):
            r = self.client.get(path)
            self.assertRedirects(r, reverse('participant_space'), msg_prefix=path)

    def test_participant_is_never_shown_as_a_member_or_author(self):
        self.assertNotContains(self.client.get(reverse('public_member_list')), 'Traoré')
        from articles.forms import ArticleForm
        self.assertNotIn(self.user, ArticleForm().fields['authors'].queryset)
        moderator = make_user('moderateur')
        self.client.force_login(moderator)
        self.assertNotContains(self.client.get(reverse('user_list')), 'awa@example.org')
        self.assertContains(self.client.get(reverse('participant_admin_list')), 'awa@example.org')

    def test_navbar_shows_my_space(self):
        self.assertContains(self.client.get(reverse('home')), 'Mon espace')

    def test_space_is_a_separate_area_with_its_own_sidebar(self):
        for name in ('participant_space', 'participant_courses', 'participant_trainings', 'participant_profile',
                     'participant_password', 'participant_membership'):
            r = self.client.get(reverse(name))
            self.assertContains(r, 'class="sp-side"', msg_prefix=name)
            self.assertNotContains(r, 'class="zabantu-footer', msg_prefix=name)   # pas l'habillage du site public

    def test_password_change_keeps_the_session(self):
        r = self.client.post(reverse('participant_password'), {
            'old_password': PASSWORD, 'new_password1': 'Encore-plus-solide-77', 'new_password2': 'Encore-plus-solide-77'})
        self.assertRedirects(r, reverse('participant_profile'))
        self.assertEqual(self.client.get(reverse('participant_space')).status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('Encore-plus-solide-77'))

    def test_profile_updates_identity(self):
        self.client.post(reverse('participant_profile'), {'prenom': 'Awa', 'nom': 'Keïta', 'status': 'chercheur',
                                                          'organization': 'USSGB', 'notify_cohorts': 'on'})
        self.user.refresh_from_db()
        self.assertEqual((self.user.nom, self.user.participant_profile.organization), ('KEÏTA', 'USSGB'))


class TrainingPagesTests(TestCase):
    def test_only_open_cohorts_are_listed_and_linked(self):
        cohort('Ouverte')
        cohort('Plus tard', days_open=(5, 20))
        cohort('Terminée', days_open=(-20, -1))
        r = self.client.get(reverse('training_list'))
        self.assertContains(r, 'Ouverte')
        self.assertNotContains(r, 'Plus tard')
        self.assertNotContains(r, 'Terminée')
        home = self.client.get(reverse('home'))
        self.assertContains(home, 'class="nav-open-pill"')                 # pastille dans le menu À propos
        self.assertContains(home, "Voir les formations et s'inscrire")      # section de l'accueil
        self.assertContains(home, 'Ouverte<small>')                         # la cohorte ouverte y est listée
        self.assertNotContains(home, 'Plus tard<small>')

    def test_no_link_or_banner_without_open_cohort(self):
        cohort('Plus tard', days_open=(5, 20))
        home = self.client.get(reverse('home'))
        self.assertContains(home, 'class="dropdown-item nav-trainings"')   # entrée permanente du menu
        self.assertNotContains(home, 'class="nav-open-pill"')
        self.assertContains(home, 'id="formations"')                      # section toujours présente
        self.assertContains(home, 'Prochaines formations')

    def test_english_name_on_the_english_page(self):
        cohort('Méthodes', name_en='Methods', description_en='Course for researchers')
        self.assertContains(self.client.get(en('training_list')), 'Methods')


class EnrollmentTests(TestCase):
    def setUp(self):
        self.cohort = cohort()
        self.user = participant()

    def test_anonymous_visitor_is_sent_to_login_then_back(self):
        url = reverse('training_enroll', args=[self.cohort.pk])
        r = self.client.get(url)
        self.assertRedirects(r, f"{reverse('login')}?next={url.replace('/', '%2F')}")

    def test_participant_enrolls_once(self):
        self.client.force_login(self.user, backend='courses.backends.ParticipantBackend')
        url = reverse('training_enroll', args=[self.cohort.pk])
        r = self.client.post(url, {'motivation': 'Renforcer mes analyses', 'expectations': ''})
        self.assertRedirects(r, reverse('participant_trainings'))
        self.assertEqual(Enrollment.objects.get().status, 'pending')
        self.assertRedirects(self.client.get(url), reverse('participant_trainings'))   # déjà inscrit
        self.assertEqual(Enrollment.objects.count(), 1)
        self.assertContains(self.client.get(reverse('training_list')), 'Demande en attente')

    def test_motivation_word_limit(self):
        self.client.force_login(self.user, backend='courses.backends.ParticipantBackend')
        r = self.client.post(reverse('training_enroll', args=[self.cohort.pk]), {'motivation': 'mot ' * 151})
        self.assertContains(r, 'Maximum 150 mots.')

    def test_closed_cohort_refuses_enrollment(self):
        closed = cohort('Terminée', days_open=(-20, -1))
        self.client.force_login(self.user, backend='courses.backends.ParticipantBackend')
        self.assertEqual(self.client.get(reverse('training_enroll', args=[closed.pk])).status_code, 404)


@override_settings(PRIVATE_MEDIA_ROOT=_PRIVATE)
class DecisionsAndAccessTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(_PRIVATE, ignore_errors=True)

    def setUp(self):
        self.course = Course.objects.create(title='Économétrie appliquée')
        self.file = CourseFile.objects.create(course=self.course, file=pdf('econometrie.pdf'))
        self.cohort = cohort()
        self.cohort.courses.add(self.course)
        self.user = participant(language='en')
        self.enrollment = Enrollment.objects.create(cohort=self.cohort, user=self.user, motivation='x')
        self.moderator = make_user('moderateur')

    def _as_participant(self):
        self.client.force_login(self.user, backend='courses.backends.ParticipantBackend')

    def test_course_files_are_stored_outside_media(self):
        path = Path(self.file.file.path)
        self.assertTrue(str(path).startswith(_PRIVATE))
        self.assertFalse(str(path).startswith(str(settings.MEDIA_ROOT)))

    def test_pending_participant_has_no_access(self):
        self._as_participant()
        self.assertEqual(self.client.get(reverse('participant_course', args=[self.course.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse('participant_course_file', args=[self.file.pk])).status_code, 404)

    def test_accept_gives_access_and_sends_an_email_in_the_participant_language(self):
        self.client.force_login(self.moderator)
        self.client.post(reverse('enrollment_admin_action', args=[self.enrollment.pk, 'accept']))
        self.enrollment.refresh_from_db()
        self.assertEqual((self.enrollment.status, self.enrollment.decided_by), ('accepted', self.moderator))
        self.assertEqual(mail.outbox[-1].subject, 'Your enrolment in “Méthodes quantitatives” has been accepted')
        self._as_participant()
        self.assertContains(self.client.get(reverse('participant_space')), 'Économétrie appliquée')
        r = self.client.get(reverse('participant_course_file', args=[self.file.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertIn('attachment; filename="econometrie.pdf"', r['Content-Disposition'])
        self.assertEqual(b''.join(r.streaming_content), b'%PDF-1.4 test')

    def test_revoke_removes_access(self):
        self.enrollment.decide('accept', self.moderator)
        self.client.force_login(self.moderator)
        self.client.post(reverse('enrollment_admin_action', args=[self.enrollment.pk, 'revoke']))
        self._as_participant()
        self.assertEqual(self.client.get(reverse('participant_course_file', args=[self.file.pk])).status_code, 404)

    def test_bulk_decision_skips_impossible_transitions(self):
        other = Enrollment.objects.create(cohort=self.cohort, user=participant('b@example.org'), motivation='y')
        other.decide('reject', self.moderator)
        self.client.force_login(self.moderator)
        r = self.client.post(reverse('enrollment_admin_bulk', args=[self.cohort.pk]),
                             {'action': 'reject', 'ids': [self.enrollment.pk, other.pk]}, follow=True)
        self.assertContains(r, '1 inscription(s) refusée(s)')
        self.assertContains(r, '1 inscription(s) ignorée(s)')
        self.assertEqual(len(mail.outbox), 1)

    def test_other_participants_and_visitors_have_no_access(self):
        self.enrollment.decide('accept', self.moderator)
        self.client.force_login(participant('c@example.org'), backend='courses.backends.ParticipantBackend')
        self.assertEqual(self.client.get(reverse('participant_course_file', args=[self.file.pk])).status_code, 404)
        self.client.logout()
        r = self.client.get(reverse('participant_course_file', args=[self.file.pk]))
        self.assertEqual(r.status_code, 302)

    def test_staff_can_preview_courses(self):
        self.client.force_login(self.moderator)
        self.assertEqual(self.client.get(reverse('participant_course', args=[self.course.pk])).status_code, 200)

    def test_backoffice_pages_and_file_upload(self):
        self.client.force_login(self.moderator)
        for name, args in (('course_admin_list', []), ('course_admin_detail', [self.course.pk]),
                           ('cohort_admin_list', []), ('cohort_admin_detail', [self.cohort.pk]),
                           ('participant_admin_list', []), ('course_admin_create', []), ('cohort_admin_create', [])):
            self.assertEqual(self.client.get(reverse(name, args=args)).status_code, 200, name)
        r = self.client.post(reverse('course_admin_detail', args=[self.course.pk]),
                             {'files': [pdf('a.pdf'), pdf('b.pdf')]})
        self.assertEqual(self.course.files.count(), 3)
        r = self.client.post(reverse('course_admin_detail', args=[self.course.pk]),
                             {'files': [SimpleUploadedFile('virus.exe', b'MZ')]})
        self.assertContains(r, 'virus.exe : Format non accepté')
        self.assertEqual(self.course.files.count(), 3)


class AnnouncementTests(TestCase):
    def test_opening_is_announced_once_to_participants_who_want_it(self):
        participant('a@example.org', language='en')
        participant('b@example.org', notify=False)
        participant('c@example.org', active=False)
        make_user('membre')
        cohort('Méthodes', name_en='Methods')
        cohort('Plus tard', days_open=(3, 10))
        call_command('send_pending_emails', stdout=open('/dev/null', 'w'))
        self.assertEqual([m.to for m in mail.outbox], [['a@example.org']])
        self.assertEqual(mail.outbox[0].subject, 'New training open: Methods')
        call_command('send_pending_emails', stdout=open('/dev/null', 'w'))
        self.assertEqual(len(mail.outbox), 1)                          # une seule fois
        self.assertEqual(CohortAnnouncement.objects.exclude(sent_at=None).count(), 1)

    def test_participant_can_turn_announcements_off(self):
        user = participant()
        self.client.force_login(user, backend='courses.backends.ParticipantBackend')
        self.client.post(reverse('participant_profile'), {'prenom': 'Awa', 'nom': 'Traoré', 'status': 'chercheur',
                                                          'organization': 'USSGB'})
        user.participant_profile.refresh_from_db()
        self.assertEqual((user.participant_profile.status, user.participant_profile.notify_cohorts), ('chercheur', False))


class CacheTests(TestCase):
    def test_participant_signup_does_not_reset_the_page_cache(self):
        from site_web import content_cache
        before = content_cache.content_version()
        participant()
        self.assertEqual(content_cache.content_version(), before)


class MembershipFromTheSpaceTests(TestCase):
    """Un participant demande l'adhésion depuis son espace (formulaire allégé) ; validé, il devient membre et garde
    son espace ; révoqué, il redevient participant."""

    def setUp(self):
        self.user = participant()
        self.client.force_login(self.user, backend='courses.backends.ParticipantBackend')

    def _apply(self):
        return self.client.post(reverse('participant_membership'), {
            'city_country': 'Bamako, Mali', 'institution': 'ONG Sahel', 'phone': '',
            'research_interests': 'Économie rurale', 'contribution': 'Participer aux séminaires', 'consent': 'on'})

    def test_light_form_creates_a_prefilled_application(self):
        from site_web.models import MembershipApplication
        r = self._apply()
        self.assertRedirects(r, reverse('participant_membership'))
        application = MembershipApplication.objects.get()
        self.assertEqual((application.full_name, application.email, application.academic_status, application.status),
                         ('Awa TRAORÉ', 'awa@example.org', 'professionnel', 'pending'))
        self.assertEqual(mail.outbox[-1].subject, "Votre demande d'adhésion à Zabantu")
        self.assertContains(self.client.get(reverse('participant_membership')), "Demande en cours d")

    def test_approval_makes_a_member_who_keeps_the_space_and_revocation_brings_back_a_participant(self):
        from site_web.models import MembershipApplication
        self._apply()
        application = MembershipApplication.objects.get()
        moderator = make_user('moderateur')
        application.approve(moderator)
        self.user.refresh_from_db()
        self.assertEqual((self.user.role, self.user.is_active), ('membre', True))
        self.assertContains(self.client.get(reverse('public_member_list')), 'TRAORÉ')
        self.client.logout()
        r = self.client.post(reverse('login'), {'identifier': 'awa@example.org', 'password': PASSWORD})
        self.assertRedirects(r, reverse('participant_space'))                    # l'espace reste accessible
        self.assertContains(self.client.get(reverse('participant_membership')), 'Vous êtes membre')
        application.revoke(moderator)
        self.user.refresh_from_db()
        self.assertEqual((self.user.role, self.user.is_active), ('participant', True))
