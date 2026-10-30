from django.core.management.base import BaseCommand

from gallery.models import Gallery, Photo
from site_web.thumbnails import get_thumbnail


class Command(BaseCommand):
    help = ("Pré-génère les miniatures des photos et couvertures de galeries. "
            "Les originaux et la base de données ne sont jamais modifiés.")

    def add_arguments(self, parser):
        parser.add_argument('--width', type=int, action='append',
                            help="Largeur(s) à générer (défaut : 640 et 1600).")

    def handle(self, *args, **options):
        widths = options['width'] or [640, 1600]
        images = [p.image for p in Photo.objects.exclude(image='')]
        images += [g.cover_image for g in Gallery.objects.exclude(cover_image='').exclude(cover_image__isnull=True)]
        done = 0
        for image in images:
            for width in widths:
                get_thumbnail(image, width)
                done += 1
        self.stdout.write(self.style.SUCCESS(f"{len(images)} image(s) traitée(s), {done} miniature(s) vérifiée(s)/créée(s)."))
