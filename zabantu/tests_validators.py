import io

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from PIL import Image

from gallery.models import Photo
from users.testing import make_user
from zabantu.validators import validate_image, validate_pdf


def image_bytes(fmt='PNG', size=(20, 20)):
    buf = io.BytesIO()
    Image.new('RGB', size, 'green').save(buf, fmt)
    return buf.getvalue()


def upload(name, content):
    return SimpleUploadedFile(name, content)


class ImageValidatorTests(TestCase):
    def test_valid_image_is_accepted(self):
        validate_image(upload('photo.png', image_bytes()))
        validate_image(upload('PHOTO.JPG', image_bytes('JPEG')))

    def test_refuses_wrong_extension_fake_content_and_oversize(self):
        with self.assertRaises(ValidationError):
            validate_image(upload('script.svg', b'<svg onload=alert(1)>'))
        with self.assertRaises(ValidationError):
            validate_image(upload('page.php.png', b'<?php echo 1; ?>'))     # extension correcte, contenu faux
        big = upload('grosse.png', image_bytes())
        big.size = 11 * 1024 * 1024
        with self.assertRaises(ValidationError):
            validate_image(big)

    def test_existing_stored_files_are_never_rechecked(self):
        photo = Photo(title='x', image='galleries/ancienne.bmp')           # fichier déjà enregistré
        validate_image(photo.image)                                        # ne lève rien et n'ouvre rien


class PdfValidatorTests(TestCase):
    def test_pdf_checks(self):
        validate_pdf(upload('livre.pdf', b'%PDF-1.7 contenu'))
        with self.assertRaises(ValidationError):
            validate_pdf(upload('livre.exe', b'%PDF-1.7'))
        with self.assertRaises(ValidationError):
            validate_pdf(upload('faux.pdf', b'MZ\x90\x00'))


class BulkPhotoUploadTests(TestCase):
    def setUp(self):
        self.user = make_user('admin')
        self.client.force_login(self.user)

    def test_bad_file_blocks_the_whole_batch(self):
        before = Photo.objects.count()
        self.client.post(reverse('photo_create'), {
            'title': 'Lot', 'is_standalone': 'on',
            'images': [upload('bonne.png', image_bytes()), upload('mauvaise.png', b'pas une image')],
        })
        self.assertEqual(Photo.objects.count(), before)

    def test_good_files_are_saved(self):
        before = Photo.objects.count()
        self.client.post(reverse('photo_create'), {
            'title': 'Lot', 'is_standalone': 'on',
            'images': [upload('a.png', image_bytes()), upload('b.jpg', image_bytes('JPEG'))],
        })
        self.assertEqual(Photo.objects.count(), before + 2)
