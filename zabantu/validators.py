"""Contrôle des fichiers téléversés : type, poids, contenu réel.

Les validateurs ne vérifient que les NOUVEAUX fichiers : un fichier déjà enregistré n'est jamais rouvert, ce qui permet de
modifier une fiche existante même si son ancien fichier ne respecte pas ces règles.
"""
import os

from django.core.exceptions import ValidationError
from PIL import Image

IMAGE_EXTENSIONS = ('jpg', 'jpeg', 'png', 'webp', 'gif')
MAX_IMAGE_MB = 10
MAX_PDF_MB = 25


def _is_new_upload(upload):
    return not getattr(upload, '_committed', False)


def _extension(upload):
    return os.path.splitext(getattr(upload, 'name', '') or '')[1].lower().lstrip('.')


def _check_size(upload, max_mb):
    if upload.size > max_mb * 1024 * 1024:
        raise ValidationError(f"Le fichier ne doit pas dépasser {max_mb} Mo.", code='file_too_large')


def validate_image(upload):
    """Image JPG, PNG, WebP ou GIF de {MAX_IMAGE_MB} Mo au plus, réellement lisible comme image."""
    if not _is_new_upload(upload):
        return
    if _extension(upload) not in IMAGE_EXTENSIONS:
        raise ValidationError(
            "Format non accepté : utilisez une image " + ', '.join(e.upper() for e in IMAGE_EXTENSIONS) + '.',
            code='invalid_image_extension')
    _check_size(upload, MAX_IMAGE_MB)
    fileobj = getattr(upload, 'file', upload)
    try:
        fileobj.seek(0)
        Image.open(fileobj).verify()
    except Exception:
        raise ValidationError("Ce fichier n'est pas une image valide.", code='invalid_image')
    finally:
        fileobj.seek(0)


def validate_pdf(upload):
    """Fichier PDF de {MAX_PDF_MB} Mo au plus, dont le contenu commence bien par l'en-tête PDF."""
    if not _is_new_upload(upload):
        return
    if _extension(upload) != 'pdf':
        raise ValidationError("Format non accepté : utilisez un fichier PDF.", code='invalid_pdf_extension')
    _check_size(upload, MAX_PDF_MB)
    fileobj = getattr(upload, 'file', upload)
    try:
        fileobj.seek(0)
        header = fileobj.read(5)
    finally:
        fileobj.seek(0)
    if header != b'%PDF-':
        raise ValidationError("Ce fichier n'est pas un PDF valide.", code='invalid_pdf')
