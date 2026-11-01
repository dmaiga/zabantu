from django.test import SimpleTestCase

from gallery.models import Photo, is_raw_filename


class RawFilenameTitleTests(SimpleTestCase):
    def test_raw_camera_and_messaging_names_are_detected(self):
        for raw in ('IMG-20240803-WA0047', 'IMG_1234.JPG', 'DSC01234', 'PXL_20240803_121212345',
                    'WhatsApp Image 2024-08-03 at 10.12.33', 'Screenshot 2024-08-03', '20240803_121212',
                    '3f2a9c1e-7b4d-4e0a-9c1e-1234567890ab'):
            self.assertTrue(is_raw_filename(raw), raw)

    def test_real_titles_are_kept(self):
        for title in ('Séminaire Gɛlɛkan à Bamako', 'Atelier 2024', 'Ouverture du colloque', 'Photo de groupe'):
            self.assertFalse(is_raw_filename(title), title)
            self.assertEqual(Photo(title=title).display_title, title)

    def test_display_title_is_empty_for_raw_names(self):
        self.assertEqual(Photo(title='IMG-20240803-WA0047').display_title, '')
