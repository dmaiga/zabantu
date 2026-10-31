import os
import subprocess
import sys
from pathlib import Path

from django.test import SimpleTestCase

BASE = Path(__file__).resolve().parent.parent


def root_settings(**env):
    """STATIC_ROOT et MEDIA_ROOT tels que les calcule settings.py avec ces variables d'environnement."""
    environ = {k: v for k, v in os.environ.items() if k not in ('STATIC_ROOT', 'MEDIA_ROOT')}
    environ.update(DJANGO_SETTINGS_MODULE='zabantu.settings_test', **env)
    code = ("import django; django.setup(); from django.conf import settings as s; "
            "print(s.STATIC_ROOT); print(s.MEDIA_ROOT)")
    out = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, cwd=BASE, env=environ, timeout=60)
    assert out.returncode == 0, out.stderr
    static, media = out.stdout.split()
    return static, media


class FileRootsTests(SimpleTestCase):
    def test_defaults_are_the_project_folders(self):
        self.assertEqual(root_settings(), (str(BASE / 'staticfiles'), str(BASE / 'media')))

    def test_relative_values_are_relative_to_the_project_root(self):
        self.assertEqual(root_settings(STATIC_ROOT='staticfiles', MEDIA_ROOT='media'),
                         (str(BASE / 'staticfiles'), str(BASE / 'media')))
        self.assertEqual(root_settings(MEDIA_ROOT='data/site/media')[1], str(BASE / 'data/site/media'))

    def test_absolute_values_are_kept_as_they_are(self):
        self.assertEqual(root_settings(STATIC_ROOT='/home/exemple/public_html/static',
                                       MEDIA_ROOT='/home/exemple/public_html/media'),
                         ('/home/exemple/public_html/static', '/home/exemple/public_html/media'))


class ProductionRequiresFileRootsTests(SimpleTestCase):
    """Un oubli de STATIC_ROOT / MEDIA_ROOT en production doit arrêter le démarrage, pas faire perdre les images."""

    def start(self, **env):
        environ = {k: v for k, v in os.environ.items() if k not in ('STATIC_ROOT', 'MEDIA_ROOT')}
        environ.update(DJANGO_SETTINGS_MODULE='zabantu.settings_test', DEBUG='False', SECRET_KEY='cle-de-test',
                       ALLOWED_HOSTS='exemple.org', **env)
        return subprocess.run([sys.executable, '-c', 'import django; django.setup()'], capture_output=True, text=True,
                              cwd=BASE, env=environ, timeout=60)

    def test_missing_media_root_stops_the_start(self):
        result = self.start(STATIC_ROOT='/srv/static', MEDIA_ROOT='')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('MEDIA_ROOT', result.stderr)

    def test_missing_static_root_stops_the_start(self):
        result = self.start(STATIC_ROOT='', MEDIA_ROOT='/srv/media')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('STATIC_ROOT', result.stderr)

    def test_both_given_starts_normally(self):
        result = self.start(STATIC_ROOT='/home/cp2594820p30/public_html/static', MEDIA_ROOT='/home/cp2594820p30/public_html/media')
        self.assertEqual(result.returncode, 0, result.stderr[-300:])

    def test_development_does_not_need_them(self):
        environ = {k: v for k, v in os.environ.items() if k not in ('STATIC_ROOT', 'MEDIA_ROOT')}
        environ.update(DJANGO_SETTINGS_MODULE='zabantu.settings_test', DEBUG='True')
        result = subprocess.run([sys.executable, '-c', 'import django; django.setup()'], capture_output=True, text=True,
                                cwd=BASE, env=environ, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr[-300:])
