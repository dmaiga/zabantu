from django.core.management.base import BaseCommand
from django.db import transaction

from site_web.models import NewsletterSubscriber
from users.models import CustomUser


class Command(BaseCommand):
    help = (
        "Abonne à l'info-lettre les comptes actifs qui ne le sont pas encore (sans doublon). "
        "Attention : ces personnes n'ont pas donné leur accord pour l'info-lettre ; à n'utiliser qu'en connaissance de cause."
    )

    def handle(self, *args, **kwargs):
        existing_emails = set(NewsletterSubscriber.objects.values_list('email', flat=True))
        users = CustomUser.objects.filter(is_active=True, email__isnull=False).exclude(email__exact='')

        to_create = []
        for user in users:
            email = user.email.lower().strip()
            if email not in existing_emails:
                to_create.append(NewsletterSubscriber(email=email))

        with transaction.atomic():
            NewsletterSubscriber.objects.bulk_create(to_create, ignore_conflicts=True)

        self.stdout.write(self.style.SUCCESS(f'{len(to_create)} nouveaux abonnés ajoutés'))
