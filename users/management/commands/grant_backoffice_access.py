from django.core.management.base import BaseCommand, CommandError

from users.models import CustomUser


class Command(BaseCommand):
    help = (
        "Donne (ou retire avec --revoke) l'accès à la connexion du backoffice aux comptes indiqués, par nom d'utilisateur. "
        "Ne modifie que le champ « accès au backoffice »."
    )

    def add_arguments(self, parser):
        parser.add_argument('usernames', nargs='+', help="Un ou plusieurs noms d'utilisateur")
        parser.add_argument('--revoke', action='store_true', help="Retire l'accès au lieu de l'accorder")

    def handle(self, *args, **options):
        value = not options['revoke']
        missing = []
        for username in options['usernames']:
            user = CustomUser.objects.filter(username=username).first()
            if user is None:
                missing.append(username)
                self.stderr.write(self.style.ERROR(f'Introuvable : {username}'))
                continue
            if user.backoffice_access == value:
                self.stdout.write(f'Déjà {"autorisé" if value else "retiré"} : {username}')
                continue
            user.backoffice_access = value
            user.save(update_fields=['backoffice_access'])
            self.stdout.write(self.style.SUCCESS(f'{"Accès accordé" if value else "Accès retiré"} : {username}'))

        if missing:
            raise CommandError(f'{len(missing)} compte(s) introuvable(s) : {", ".join(missing)}')
