from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect

# Adresses du backoffice. Beaucoup de vues n'exigent qu'une connexion : un compte participant connecté y entrerait.
BACKOFFICE_PREFIXES = ('/users/', '/articles/', '/events/', '/gallery/', '/intervenants/', '/courses/', '/tinymce/',
                       '/admin/')


class BackofficeGuardMiddleware:
    """Ferme tout le backoffice aux comptes connectés qui n'y ont pas accès (participants) : retour à « Mon espace »."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        if (user is not None and user.is_authenticated and not user.can_access_backoffice
                and request.path_info.startswith(BACKOFFICE_PREFIXES)):
            messages.info(request, "Votre compte donne accès à votre espace de formation, pas à l'espace de gestion.")
            return redirect('participant_space')
        return self.get_response(request)
