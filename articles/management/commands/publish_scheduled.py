from django.core.management.base import BaseCommand
from django.utils import timezone
from articles.models import Article

class Command(BaseCommand):
    help = 'Publie les articles planifiés'

    def handle(self, *args, **options):
        now = timezone.now()
        to_publish = Article.objects.filter(
            publish_at__lte=now,
            status='draft'
        )
        
        count = to_publish.update(status='published')
        self.stdout.write(f"{count} articles publiés automatiquement")