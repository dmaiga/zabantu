from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def moderator_required(view):
    """Réserve une vue aux administrateurs et modérateurs (403 pour les autres connectés)."""
    @wraps(view)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.can_moderate:
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return wrapper
