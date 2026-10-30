"""Miniatures à la demande, sans toucher aux originaux ni à la base de données.

Les miniatures sont écrites dans MEDIA_ROOT/cache/thumbs/. Si le dossier n'est pas
accessible en écriture, ou si l'image est illisible, l'original est renvoyé tel quel :
une miniature manquante ne casse jamais une page. Supprimer le dossier cache/thumbs
suffit à tout annuler.
"""
import hashlib
import logging
from dataclasses import dataclass
from io import BytesIO
from typing import Optional

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from PIL import Image, ImageOps

logger = logging.getLogger(__name__)

THUMB_DIR = 'cache/thumbs'
JPEG_QUALITY = 82


@dataclass
class Thumb:
    url: str
    width: Optional[int] = None      # dimensions de l'image servie
    height: Optional[int] = None
    src_width: Optional[int] = None  # dimensions de l'original
    src_height: Optional[int] = None


def _name_and_storage(image):
    """Accepte un champ image (ImageFieldFile) ou un simple nom de fichier."""
    if hasattr(image, 'name') and hasattr(image, 'storage'):
        return image.name, image.storage
    return str(image), default_storage


def get_thumbnail(image, width):
    """Renvoie un Thumb de largeur `width` ; repli sur l'original en cas de souci."""
    if not image:
        return Thumb(url='')
    name, storage = _name_and_storage(image)
    original_url = storage.url(name)
    try:
        with storage.open(name) as fh:
            with Image.open(fh) as src:
                src_w, src_h = ImageOps.exif_transpose(src).size
    except Exception:
        logger.warning("Miniature : original illisible %s", name, exc_info=True)
        return Thumb(url=original_url)

    if src_w <= width:  # déjà assez petite : on sert l'original
        return Thumb(url=original_url, width=src_w, height=src_h, src_width=src_w, src_height=src_h)

    height = round(src_h * width / src_w)
    key = hashlib.sha1(f"{name}|{width}|{src_w}x{src_h}".encode()).hexdigest()
    thumb_name = f"{THUMB_DIR}/{width}/{key}.jpg"
    try:
        if not storage.exists(thumb_name):
            with storage.open(name) as fh:
                with Image.open(fh) as src:
                    img = ImageOps.exif_transpose(src)
                    if img.mode in ('RGBA', 'LA', 'P'):
                        img = img.convert('RGBA')
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        background.paste(img, mask=img.split()[-1])
                        img = background
                    else:
                        img = img.convert('RGB')
                    img = img.resize((width, height), Image.LANCZOS)
                    buffer = BytesIO()
                    img.save(buffer, 'JPEG', quality=JPEG_QUALITY, optimize=True, progressive=True)
            storage.save(thumb_name, ContentFile(buffer.getvalue()))
        return Thumb(url=storage.url(thumb_name), width=width, height=height,
                     src_width=src_w, src_height=src_h)
    except Exception:
        logger.warning("Miniature : génération impossible pour %s", name, exc_info=True)
        return Thumb(url=original_url, src_width=src_w, src_height=src_h)
