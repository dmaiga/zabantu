# articles/media_library.py
from django.core.files.storage import default_storage
import os

def list_media_files():
    media_dir = 'articles/'
    files = []
    for root, dirs, filenames in os.walk(default_storage.path(media_dir)):
        for filename in filenames:
            files.append(os.path.join(root, filename).replace(default_storage.path(''), ''))
    return files