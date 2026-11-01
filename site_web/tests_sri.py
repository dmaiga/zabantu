import re
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

# Chargé sans empreinte et sans contrôle possible : feuille de polices Google (contenu variable selon le navigateur)
EXEMPT = ('fonts.googleapis.com',)
TAG = re.compile(r'<(?:link|script)\b[^>]*(?:href|src)="https://[^"]+"[^>]*>', re.IGNORECASE)


class ExternalLibrariesHaveIntegrityTests(SimpleTestCase):
    def test_every_external_stylesheet_and_script_has_an_integrity_hash(self):
        missing = []
        for path in Path(settings.BASE_DIR).glob('*/templates/**/*.html'):
            if 'emails' in path.parts:       # e-mails : hors du site, aucun script
                continue
            for tag in TAG.findall(path.read_text(encoding='utf-8')):
                is_asset = 'rel="stylesheet"' in tag or '<script' in tag.lower()
                if is_asset and not any(host in tag for host in EXEMPT) and 'integrity="sha' not in tag:
                    missing.append(f'{path.relative_to(settings.BASE_DIR)} : {tag[:90]}')
                if 'integrity=' in tag and 'crossorigin=' not in tag:
                    missing.append(f'{path.relative_to(settings.BASE_DIR)} : crossorigin manquant')
        self.assertEqual(missing, [])
