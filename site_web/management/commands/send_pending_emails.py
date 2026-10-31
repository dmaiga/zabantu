import fcntl
import tempfile
from pathlib import Path

from django.core.management.base import BaseCommand

from site_web import mailing


class Command(BaseCommand):
    help = (
        "Envoie par lots les annonces de publication en attente et retente celles en échec. "
        "Déjà appelée par publish_scheduled ; à lancer seule si besoin (voir docs/DEPLOIEMENT_PROD.md)."
    )

    def handle(self, *args, **options):
        # Un seul envoi à la fois : un passage du cron encore en cours ne doit pas être doublé.
        with open(Path(tempfile.gettempdir()) / 'zabantu_send_pending.lock', 'w') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                self.stdout.write("Envoi déjà en cours : rien à faire")
                return
            sent, failed = mailing.send_pending()
        self.stdout.write(f"{sent} e-mail(s) envoyé(s), {failed} échec(s)")
