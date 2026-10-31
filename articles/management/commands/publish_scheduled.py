from django.core.management.base import BaseCommand
from django.utils import timezone

from articles.models import Article, Guelekan
from site_web.mailing import notify_publication


class Command(BaseCommand):
    help = (
        "Publie les contenus programmés dont la date est passée et les annonce aux abonnés. "
        "À lancer régulièrement par cron (voir docs/DEPLOIEMENT_PROD.md)."
    )

    def handle(self, *args, **options):
        total = 0
        for model in (Article, Guelekan):
            due = list(model.objects.filter(status='scheduled', publish_at__lte=timezone.now()))
            for item in due:
                item.status = 'published'
                item.save()
                notify_publication(item)
                self.stdout.write(f"Publié : {item.title}")
            total += len(due)
        self.stdout.write(f"{total} contenu(s) publié(s)")
