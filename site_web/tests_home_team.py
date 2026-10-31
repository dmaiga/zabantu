import io
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

U = get_user_model()


def member(i, **kw):
    defaults = dict(username=f'm{i}', email=f'm{i}@t.org', password='x', nom=f'Nom{i}', prenom='Prenom', role='membre')
    defaults.update(kw)
    return U.objects.create_user(**defaults)


def photo():
    buffer = io.BytesIO()
    Image.new('RGB', (30, 40), 'green').save(buffer, 'PNG')
    return SimpleUploadedFile('p.png', buffer.getvalue(), content_type='image/png')


class HomeTeamCarouselTests(TestCase):
    def setUp(self):
        for i in range(8):
            member(i)
        member(20, role='moderateur')
        member(21, is_active=False)
        member(22, role='admin')

    def home(self):
        return self.client.get(reverse('home'))

    def test_every_active_member_and_moderator_is_in_the_carousel(self):
        team = list(self.home().context['team_members'])
        self.assertEqual(len(team), 9)  # plus de limite à 4 ; ni inactif ni administrateur
        roles = {m.role for m in team}
        self.assertEqual(roles, {'membre', 'moderateur'})
        self.assertTrue(all(m.is_active for m in team))

    def test_order_is_random_from_one_load_to_the_next(self):
        orders = {tuple(m.pk for m in self.home().context['team_members']) for _ in range(12)}
        self.assertGreater(len(orders), 1)
        self.assertEqual(len({frozenset(o) for o in orders}), 1)  # toujours les mêmes membres

    def test_markup_is_an_accessible_carousel(self):
        html = self.home().content.decode()
        for expected in ('data-team-carousel', 'role="region"', 'aria-roledescription="carrousel"',
                         'aria-label="Membres précédents"', 'aria-label="Membres suivants"',
                         'aria-label="Mettre en pause le défilement"', 'prefers-reduced-motion'):
            self.assertIn(expected, html, expected)
        self.assertEqual(html.count('class="team-card"'), 9)

    def test_frame_is_rectangular_and_shows_the_whole_photo(self):
        html = self.home().content.decode()
        css = html.split('.team-photo {')[1].split('}')[0]
        self.assertIn('aspect-ratio: 3 / 4', css)
        self.assertNotIn('50%', css)  # plus de médaillon ovale
        self.assertIn('object-fit: contain', html.split('.team-photo-img {')[1].split('}')[0])
        self.assertNotIn('.team-mini img { width: 110px', html)

    def test_card_uses_the_photo_or_initials(self):
        media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, media, True)
        with override_settings(MEDIA_ROOT=media):
            with_photo = member(30)
            with_photo.profile_picture.save('p.png', photo(), save=True)
            html = self.home().content.decode()
        self.assertIn('class="team-photo-img"', html)
        self.assertIn('team-initials', html)  # les autres membres n'ont pas de photo
        card = html.split(f'/zabantu/membres/{with_photo.pk}/')[1].split('</li>')[0]
        self.assertIn('class="team-photo-bg"', card)
        self.assertIn('alt=""', card.split('class="team-photo-bg"')[1][:120])  # le fond flou est décoratif

    def test_no_members_means_no_section(self):
        U.objects.all().delete()
        self.assertNotContains(self.home(), 'data-team-carousel')


class AboutPageCarouselTests(TestCase):
    def setUp(self):
        for i in range(8):
            member(i, bio='<p>' + ' '.join(f'mot{j}' for j in range(30)) + '</p>')
        member(20, is_active=False)
        member(21, role='admin')

    def about(self):
        return self.client.get(reverse('about'))

    def test_about_page_has_the_same_carousel_with_every_active_member(self):
        r = self.about()
        self.assertEqual(len(r.context['team_members']), 8)
        html = r.content.decode()
        self.assertIn('data-team-carousel', html)
        self.assertEqual(html.count('class="team-card"'), 8)
        self.assertNotIn('class="team-grid"', html)

    def test_about_order_is_random(self):
        orders = {tuple(m.pk for m in self.about().context['team_members']) for _ in range(12)}
        self.assertGreater(len(orders), 1)

    def test_about_keeps_its_links_to_the_full_list_and_to_membership(self):
        html = self.about().content.decode()
        self.assertIn(reverse('public_member_list'), html)
        self.assertIn(reverse('membership_apply'), html)

    def test_frame_is_the_shared_rectangular_one_on_both_pages(self):
        for name in ('home', 'about'):
            html = self.client.get(reverse(name)).content.decode()
            self.assertIn('.team-photo { position: relative; aspect-ratio: 3 / 4', html, name)


class FullMemberListFrameTests(TestCase):
    def setUp(self):
        for i in range(6):
            member(i)

    def test_cards_use_the_whole_photo_frame_and_no_orientation_script(self):
        html = self.client.get(reverse('public_member_list')).content.decode()
        self.assertIn('.team-photo { position: relative; aspect-ratio: 3 / 4', html)
        self.assertEqual(html.count('class="card member-card'), 6)
        self.assertEqual(html.count('team-initials'), 6 + html.count('.team-initials {'))  # pas de photo : initiales
        self.assertNotIn('checkImageOrientation', html)
        self.assertNotIn('img-container', html)

    def test_cards_stay_four_across_on_wide_screens(self):
        html = self.client.get(reverse('public_member_list')).content.decode()
        self.assertEqual(html.count('col-sm-6 col-md-4 col-xl-3'), 6)

    def test_card_footer_wraps_instead_of_crowding_the_social_icons(self):
        html = self.client.get(reverse('public_member_list')).content.decode()
        self.assertIn('justify-content-between align-items-center flex-wrap gap-2', html)
