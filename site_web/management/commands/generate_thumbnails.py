from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from articles.models import Article, Guelekan
from events.models import Event
from gallery.models import Gallery, Photo
from intervenants.models import Intervenant
from site_web.thumbnails import get_thumbnail


def _files(queryset, field):
    """Fichiers non vides du champ image `field`."""
    return [getattr(obj, field) for obj in queryset.exclude(**{field: ''}).exclude(**{f'{field}__isnull': True})]


class Command(BaseCommand):
    help = ("Pré-génère les miniatures servies par le site public (galeries, couvertures, portraits). "
            "Les originaux et la base de données ne sont jamais modifiés.")

    def add_arguments(self, parser):
        parser.add_argument('--width', type=int, action='append',
                            help="Largeur(s) à générer pour toutes les images (défaut : celles utilisées par les pages).")

    def handle(self, *args, **options):
        # (images, largeurs utilisées par les gabarits publics)
        groups = [
            (_files(Photo.objects.all(), 'image') + _files(Gallery.objects.all(), 'cover_image'), [640, 1600]),
            (_files(Article.objects.all(), 'cover_image') + _files(Article.objects.all(), 'independent_cover')
             + _files(Guelekan.objects.all(), 'cover_image') + _files(Event.objects.all(), 'image'), [640, 1600]),
            (_files(get_user_model().objects.all(), 'profile_picture'), [640, 160]),
            (_files(Intervenant.objects.all(), 'photo'), [320]),
        ]
        images = done = 0
        for files, widths in groups:
            widths = options['width'] or widths
            for image in files:
                images += 1
                for width in widths:
                    get_thumbnail(image, width)
                    done += 1
        self.stdout.write(self.style.SUCCESS(f"{images} image(s) traitée(s), {done} miniature(s) vérifiée(s)/créée(s)."))
